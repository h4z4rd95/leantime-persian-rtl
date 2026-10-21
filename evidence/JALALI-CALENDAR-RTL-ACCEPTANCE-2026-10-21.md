# T-2026-10-22 — Jalali calendar + RTL acceptance: evidence report

Task: `h4z4rd95/Plan-Project-Situation` prompt
`T-2026-10-22-LEANTIME-JALALI-CALENDAR-AND-RTL-ACCEPTANCE-001.md`.
Controlling issues: #3 (P0 RTL repair) and #5 (RTL UI audit). Work done on
branch `fix/rtl-row-gutter-overflow` (continuation), repo
`h4z4rd95/leantime-persian-rtl`. No production deployment, no DB/schema
change, no core file edit.

## 1. Reconciliation (branch / live / rollback)

| Item | State |
|---|---|
| `main` HEAD | `77c93a9` (translation workflow) — does NOT contain the RTL gutter fix |
| Existing fix branch | `fix/rtl-row-gutter-overflow @ 5646739` — row-gutter overflow fix + guard, **not merged, not deployed** |
| Production container | `code-leantime-1`, `leantime/leantime:3.10.0`, overlay installed. Served `custom.min.css` md5 `e0a2cecd…` — matches NEITHER `main` (`131b51ae…`) NOR the fix branch (`c97bbea5…`; the production copy predates both). Grep of the live file still contains the mirrored-gutter regression `margin-right:-20px`; `firstDayOfWeek="0"`, `monthNames="January,…”` |
| Isolated test instance | `rtl-leantime` + `rtl-db` (MariaDB 11), `127.0.0.1:8123`, `LEAN_APP_URL=http://localhost:8123`, image pinned to `3.10.0`. Overlay from the fix branch applied; served CSS/INI verified byte-identical to the repo files (`diff -q`) after cache+view clear and restart |
| Rollback material | Per-file `git checkout <sha> -- <path>` in the repo + redeploy of the overlay via the same `docker cp` path; production untouched (no deploy). DB untouched. `/root/lt-backup-pre-p0/` still present |

## 2. RTL row-gutter fix — re-verified on this instance

Guard `scripts/check_rtl_row_gutter.py` passes on the branch (exit 0).

Acceptance matrix (rect scan, elements with `rect.right > innerWidth + 1`,
Vazirmatn + `dir=rtl` + `lang=fa-IR` asserted at every measurement):

| Route | 1440 right | 1024 right | 390 right | Notes |
|---|---|---|---|---|
| `/dashboard/home` | 0 | 1 | 0 | `div.bar` = empty, absolute-positioned 3px-tall placeholder (documented noise) |
| `/setting/editCompanySettings` | 0 | 1 | 0 | `input[type=file]`, opacity 0, `.btn-file` oversize trick (documented noise). No page scroll: `scrollWidth == innerWidth` at 1440 |
| `/calendar/showMyCalendar` | 0 | 0 | 7 | See §4 mobile note |
| `/projects/showProjects` | 0 | 0 | 0 | clean |
| `/tickets/showKanban` | 0 | 0 | 0 | mobile: left hits are the collapsed off-canvas `.leftpanel` (theme behavior) |

Before/after reproduction of the defect on the live settings page (variant
injection of the OLD mirrored-gutter rule `html[dir="rtl"] .row{margin-left:0;
margin-right:-20px !important}`): **16 elements** pushed 10px past the right
edge at 390px (`.row`, `.col-md-2`, …). Removing the variant returns to 0.

## 3. Calendar component + date API audit (exact behavior)

Stack (read from the live container, no file edits):

- View: `app/Domain/Calendar/Templates/showMyCalendar.blade.php` instantiates
  `FullCalendar.Calendar`, `headerToolbar:false`, custom toolbar buttons,
  `firstDay: leantime.i18n.__("language.firstDayOfWeek")`,
  `dayHeaderFormat`/time formats from `leantime.dateHelper.getFormatFromSettings`,
  then `calendar.setOption('locale', leantime.i18n.__("language.code"))`
  (`language.code = "fa-IR"`).
- FullCalendar is v6 (bundle `public/dist/js/compiled-calendar-component.3.10.0.min.js`;
  `FullCalendar.globalLocales` is EMPTY on the page — no FC-registered Persian
  locale data).
- Storage/round-trip contract:
  - server renders events as `new Date(<UTC ms>)` → FC positions them;
  - drag/resize write back ISO `startStr`/`endStr` through
    `leantime.rpc('Calendar.Calendar.patch', {dateFrom, dateTo})` and
    `Tickets.Tickets.patchTicket` (`editFrom`, `editTo`, `dateToFinish`);
  - server `app/Core/Support/DateTimeHelper::parseUserDateTime` parses user
    strings with `CarbonImmutable::createFromLocaleFormat('!'.userDateFormat,
    locale, …)`; DB format `Y-m-d H:i:s` in UTC (`dbTimezone = 'UTC'`).
- Date entry: `app/Domain/Calendar/Js/calendarController.js::initEventDatepickers`
  configures jQuery UI datepickers straight from the `fa-IR` INI keys fixed
  here (`monthNames`, `dayNames*`, `firstDay`, button texts).

### Verified round-trip (Gregorian/UTC preserved, step 4 of the prompt)

1. Picked Oct 15→17 in the Persian-labeled picker → inputs hold `10/15/2026`
   and `10/17/2026` (`m/d/Y`, the user date format).
2. POST `/calendar/addEvent` captured: `dateFrom=10/15/2026`, `dateTo=10/17/2026`.
3. DB: `zp_calendar` row 1 stored as `dateFrom=2026-10-15 07:00:00`,
   `dateTo=2026-10-17 07:00:00` (Gregorian, UTC; 07:00 = workday start from
   settings) — no Jalali/converted value anywhere in the store.
4. Simulated the `eventDrop` path verbatim:
   `leantime.rpc('Calendar.Calendar.patch', {id:1, params:{dateFrom:'2026-10-16T09:00:00+00:00', dateTo:'2026-10-18T17:00:00+00:00'}})`
   → resolved `true` → DB updated to `2026-10-16 09:00:00 / 2026-10-18 17:00:00`.
   ISO in, ISO stored: the API date contract is untouched.

## 4. Jalali decision (step 3/6 of the prompt)

What the calendar ALREADY does (verified in the real browser on the isolated
instance, locale `fa-IR`):

- `Intl.DateTimeFormat('fa-IR').resolvedOptions().calendar === 'persian'` —
  Chromium's ICU defaults `fa-IR` to the Persian (Solar Hijri) calendar;
  `Intl.DateTimeFormat('fa-IR').format(new Date(2026,9,21))` → `۲۹ مهر ۱۴۰۵`,
  and `-u-ca-gregory` → `۲۱ اکتبر ۲۰۲۶`.
- Consequence: FullCalendar (v6, Intl-based formatting, no registered locale
  data of its own) renders the `fa-IR` calendar with genuine Jalali data:
  view title `۱۴۰۵ مهر – ۱۴۰۵ آبان`; day cells run Jalali day numbers
  `۵,۶,…,۲۹,۳۰,۱,…,۱۶` (Mehr 5 = Sep 27 … Aban 16 across the October grid);
  weekday headers `یکشنبه…شنبه` (now `شنبه…` after the week-start fix).

Why no Jalali month GRID was implemented (this slice):

- FullCalendar v6 has no calendar-system abstraction; Jalali requests
  (#1813, open since 2012) and Hijri (#2105, #3267) are unresolved upstream,
  and Jalali months have 29–31 days that do not align to Gregorian grid math.
- The only community Jalali build, `mzangeneh/fullcalendar-shamsi`, is a fork
  of FullCalendar **v5.5.1**, last mid-2024, incompatible with Leantime's
  bundled v6 bundle (`compiled-calendar-component.3.10.0.min.js`).
- A Jalali date *entry* widget would need to replace the Gregorian jQuery UI
  datepicker AND keep submitting Gregorian `m/d/Y` (server parse is
  Carbon/Gregorian-only, in core `DateTimeHelper`); this is a core-template +
  dependency change, outside the overlay contract.

So: calendar behavior left unchanged; the grid math, event placement, API and
DB stay Gregorian/UTC, while the Jalali *rendering* delivered by ICU is kept
and now rides on a culturally correct Saturday-first week and Persian picker
labels. Per the prompt: this partial display is reported as-is and does NOT
count as a Jalali calendar.

### Accepted residual (not an RTL-layer defect)

At 390px the month-view day cell is ~43px while a timed event renders an
~81px `fc-event-time` string (`۰۶:۵۹ قبل‌ازظهر`); these 7 hits are all events
on 2026-10-23 (Friday) which — with the Saturday week start — land in the
week's boundary column. `document.documentElement.scrollWidth ===
innerWidth === 390` (FullCalendar clips inside `.fc`), and the behavior is
direction-independent (identical in LTR with the same settings), so it is
FullCalendar's own mobile rendering. Recorded in README "What's NOT Covered".

## 5. Locale fix (this change) — verification

`translations/fa-IR.json` (source of truth) → `scripts/build_overlay.py` →
`custom/Language/fa-IR.ini`; changed exactly 12 keys (diff = 12 lines in the
INI, 35 in the JSON): Persian month/weekday names (transliterations of the
GREGORIAN months — the picker widget is Gregorian by design), Persian picker
button texts, `language.firstDayOfWeek="6"` (Saturday).

Guards (both FAIL against the pre-fix overlay, PASS after):

```text
$ python3 scripts/check_calendar_locale.py /tmp/pre.ini  → FAIL (12 problems)
$ python3 scripts/check_calendar_locale.py               → PASS
$ python3 scripts/check_rtl_row_gutter.py                → PASS (unchanged)
```

Browser verification on the isolated instance:

- Picker title: `OCTOBER 2026` → `اکتبر 2026`; day headers `Su,Mo,Tu,We,Th,Fr,Sa` →
  `ش,ی,د,س,چ,پ,ج` (Saturday-first, 7 entries).
- Calendar week columns now start `شنبه` (Saturday); Jalali day numbers and
  the `۱۴۰۵ مهر – ۱۴۰۵ آبان` title unchanged; 8→9 events render after the
  round-trip test event was added.
- `html[dir=rtl]`, `lang=fa-IR`, computed font-family `Vazirmatn,Roboto,…`
  unchanged; RTL overflow matrix unchanged (§2); the English LTR view is
  untouched (all rules stay `[dir="rtl"]`-scoped and none of the 12 keys
  change LTR behavior — the INI is only loaded for `fa-IR`).

Unchanged (out of overlay scope, core templates):
calendar toolbar literals `Day/Week/Month/Year/today/Export/Calendars` and
the FC `dayHeaderFormat` are hardcoded English in the core blade template.

## 6. Screenshots

- `evidence/calendar-jalali-1440.png` — calendar page, Jalali title/numbers.
- `evidence/datepicker-persian.png` — add-event modal, Persian picker.

(Full DOM JSON behind the tables above was produced by the rect-scan harness;
this file is the human summary.)
