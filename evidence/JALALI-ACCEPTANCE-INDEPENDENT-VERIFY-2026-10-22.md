# T-2026-10-22 — independent re-verification (second pass)

Same task, new session: the branch state was re-verified from scratch on a
fresh isolated instance, with every claim reproduced from live tool output.
No production deploy, no DB/schema change, no core file edit.

## 1. State reconciliation (verified this session)

| Item | State |
|---|---|
| Remote branch | `fix/rtl-row-gutter-overflow @ 4bb2017518d8013a68a57c4edd0538985567ed58` |
| Fetch-back | GitHub tree API at 4bb2017 compared to `git ls-tree -r HEAD` — **identical, all 28 blob SHAs match** (checked with git's own hash-object, not a re-implementation) |
| Local workspace | clean, on the same branch/SHA |
| Production | still serves the PRE-fix overlay: live `custom.min.css` md5 `e0a2cecdaccedfdf6a2af7975d635fa4`, contains `margin-right:-20px`/`-30px` mirrored gutter; live INI grep shows English months, `firstDayOfWeek="0"` |
| Guards | `scripts/check_rtl_row_gutter.py` PASS; `scripts/check_calendar_locale.py` PASS (both against repo and against the served container copy) |
| Rollback | per-file `git checkout <sha> -- <path>` + redeploy via `scripts/deploy.py`; DB untouched; `/root/lt-backup-pre-p0/` present |

## 2. Overlay application pitfall (found and handled this session)

The stock `leantime/leantime:3.10.0` image ships **neither** `/var/www/html/custom/`
**nor** `/var/www/html/public/userfiles/rtl-fonts/`. A plain
`docker cp` into those paths fails ("no such directory") and the overlay
silently does not land — the instance then runs English text with the old
CSS while `git status` shows everything committed. Any overlay deployment must
`mkdir -p` both directories first. Documented here because the failure is
silent.

The repo also carries a **stale legacy mirror** `app/custom/Language/fa-IR.ini`
(pre-fix, English months, `firstDayOfWeek="0"`). `app/Core/Language.php` reads
only `APP_ROOT.'/custom/Language/'` with `APP_ROOT = /var/www/html`
(verified: `bootstrap/app.php` `define('APP_ROOT', dirname(__DIR__, 1))`),
so the mirror is **inert** — but if any future deploy copied it to
`app/custom/Language` expecting the overlay path, the entire calendar-locale
fix would silently revert to English. This pass synced the mirror to the
fixed overlay content (md5 `6bfd9213…`, identical to `custom/Language/fa-IR.ini`),
and `scripts/build_overlay.py` remains the single generator for the real path.

## 3. Browser matrix (this session, fresh instance, real Chromium)

Instance: `rtl-leantime` + `rtl-db` (MariaDB 11), `127.0.0.1:8123`,
`LEAN_APP_URL=http://localhost:8123`, image `leantime/leantime:3.10.0`,
overlay from the branch applied; served CSS and served INI verified
byte-identical to the repo files (`diff -q` / md5) after cache+view clear and
restart. Vazirmatn fonts fetched from jsdelivr into `/userfiles/rtl-fonts/`
(HTTP 200, 50 KB each).

Rect scan (`rect.right > innerWidth + 1` RIGHT, `-rect.left > 1` LEFT);
`document.documentElement.scrollWidth === innerWidth` at every measurement;
`dir=rtl`, `lang=fa-IR`, computed font `Vazirmatn, …` asserted throughout.

| Route | 1440 | 1024 | 390 | Classification |
|---|---|---|---|---|
| `/auth/login` (logged out) | 0 | 0 | 0 | clean at all widths |
| `/dashboard/home` | 0* | 0* | 0* | `*` = only the documented empty absolute `div.bar` placeholder |
| `/setting/editCompanySettings` | 0* | 0* | 0* | `*` = `div.bar` + opacity-0 `.btn-file` file-input trick |
| `/projects/showProjects` | 0 | 0 | 0 | clean |
| `/tickets/showKanban` | 0 | 0* | 0* | `*` = off-canvas `.leftpanel` and its submenu children |
| `/calendar/showMyCalendar` | 0 | 0* | 0* | `*` = off-canvas `.leftpanel` children |

The ≤1199px LEFT hits are the core theme's collapsed off-canvas navigation
(`@media (max-width:1199px){.mainwrapper .leftpanel{position:fixed;transform:translateX(-100%)}}`
in the shipped `main.3.10.0.min.css` — untouched by the overlay: `leftpanel`
appears 0 times in either overlay CSS file), plus its `UL.submenu`/`LI` children.
Direction-independent core behavior; no page scroll anywhere.

## 4. Calendar / Jalali behavior (independently reproduced, live browser)

- `Intl.DateTimeFormat('fa-IR').resolvedOptions().calendar === 'persian'`;
  `Intl.DateTimeFormat('fa-IR').format(2026-09-21)` → `۱۴۰۵/۷/۲۹`;
  `-u-ca-gregory` → `۲۰۲۶/۱۰/۲۱`. (ICU delivers Jalali for `fa-IR`.)
- FullCalendar v6 (no registered FC locale of its own) renders off that Intl
  data: view title `۱۴۰۵ مهر – ۱۴۰۵ آبان`; month grid day numbers run Jalali
  `۵,۶,…,۳۰,۱,…`; weekday headers Persian.
- **Week start verified geometrically, not just by DOM order**: rightmost
  column of the month grid is all Saturdays (`2026-10-03, 10, 17, 24, 31,
  11-07`); header row right-to-left reads `شنبه…یکشنبه`. DOM order stays
  Sunday-first and RTL flips presentation — the INI `firstDayOfWeek=6` is live.
- **Month navigation**: next/prev move the Jalali title
  `مهر–آبان → آبان–آذر → آذر–دی` and back; grid day numbers follow.
- **Persian jQuery UI pickers**: `اکتبر 2026` title, `ش,ی,د,س,چ,پ,ج` headers
  (Saturday-first, 7 entries).
- Round-trips (all Gregorian in the store, nothing Jalali persisted):
  - create: picker → inputs `10/15/2026`–`10/17/2026` (m/d/Y) → POST →
    DB `dateFrom=2026-10-15 16:00:00` (16:00 = 09:00 user-time converted at
    the app's default timezone UTC−7);
  - edit: picker → `dateTo 10/22/2026` → DB `2026-10-23 00:00:00`;
  - drag/drop path verbatim: `leantime.rpc('Calendar.Calendar.patch', …
    '2026-10-16T09:00:00+00:00'/'2026-10-18T17:00:00+00:00')` → resolved
    `true` → DB `2026-10-16 09:00:00 / 2026-10-18 17:00:00` exact.

## 5. Jalali decision (unchanged, re-confirmed)

No Jalali month grid was implemented: FullCalendar v6 has no calendar-system
abstraction (upstream Jalali #1813 / Hijri #3267 unresolved; the only community
Jalali build is a stale v5.5.1 fork), and Jalali *entry* would require replacing
the Gregorian jQuery UI datepicker and core `DateTimeHelper` Carbon parsing.
Calendar behavior unchanged; grid math, event placement, API and DB stay
Gregorian/UTC; the genuine Jalali *rendering* delivered by ICU is kept, now on a
Saturday-first week with Persian picker labels. Reported as a partial display,
not claimed as a Jalali calendar.

## 6. Files

- `evidence/evidence-2026-10-22-calendar-jalali-1440.png` — Jalali calendar,
  10 events rendered (incl. the round-trip event with Persian times
  `۰۴:۰۰ بعدازظهر`).
- `evidence/evidence-2026-10-22-datepicker-persian.png` — Persian picker.
- Prior pass evidence kept: `evidence/calendar-jalali-1440.png`,
  `evidence/datepicker-persian.png`,
  `evidence/JALALI-CALENDAR-RTL-ACCEPTANCE-2026-10-21.md`.
