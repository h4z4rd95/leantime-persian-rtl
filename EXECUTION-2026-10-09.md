# P0 Leantime Persian RTL — Execution Log

**Date:** 2026-10-09
**Target:** https://leantime.ppsj.ir (Leantime v3.10.0)
**Server:** gglvp-migration-01 / 65.109.210.40 (SSH key `~/.ssh/hermes_desktop_key`, via `sshn.py`)
**Source repo:** h4z4rd95/leantime-persian-rtl

## Baseline audit (real environment, before any change)

| Check | Result | Status |
|---|---|---|
| DNS leantime.ppsj.ir | → 65.109.210.40 | ✅ live on new server |
| Containers | code-leantime-1 (healthy), code-db-1 | ✅ |
| Login (real admin) | POST → 200 /dashboard/home | ✅ |
| `<html dir lang>` | `<html dir="rtl" lang="fa-IR">` | ✅ |
| i18n `language.direction` | `rtl`, `isRTL=true`, `code=fa-IR` | ✅ |
| `custom.min.css` served | 200, 17106 bytes, linked in page | ✅ |
| Vazirmatn woff2 on disk (4 files) | ✅ `/public/userfiles/rtl-fonts/` | ✅ |
| DB `usersettings.1.themeFont` | `Vazirmatn` | ✅ |
| `LEAN_LANGUAGE=fa-IR` in container env | ✅ | ✅ |

### BUGS FOUND (real, server-verified)

**B1 — Font face URL broken (CSS 404s fonts)**
`custom.min.css` declares `src:url('fonts/Vazirmatn-Regular.woff2')`. Relative to
`/theme/default/css/` this resolves to `/theme/default/css/fonts/...` which returns **302 (miss)**.
Fonts actually live at `/userfiles/rtl-fonts/*.woff2` (verified 200). So **the Vazirmatn @font-face
never loads** and the UI silently falls back to system fonts.

**B2 — Login page `themeFont` override is `roboto`, not Vazirmatn**
`<style id="fontStyleSetter">` on `/auth/login` emits `--primary-font-family: 'roboto'`.
On `/dashboard/home` (logged in) it correctly emits `'Vazirmatn'`. The unauthenticated path
does not read `usersettings`, so the DB fix from the previous session does not cover it.

**B3 — Persian translation is effectively absent**
`app/Language/fa-IR.ini` (2548 lines, ~2170 keys) contains only ~36 Persian values — everything
else is untranslated English (`label.version="Version"`, `input.placeholders.enter_email="Enter email address"`).
i18n endpoint returns 2859 keys, **0 Persian**. Dashboard after real login renders fully English
("My Projects", "Favorites", "Recent"). en-US.ini has 3506 lines, so fa-IR is also **636 keys short**.
This is the core P0 item: "ترجمه کامل" was never done.

## Execution results (2026-10-09, all verified against production)

### Fixes applied and verified

| Bug | Fix | Verification |
|---|---|---|
| **B1** font 404 | `url('fonts/...')` → `url('/userfiles/rtl-fonts/...')` in `custom.min.css` | `HEAD /userfiles/rtl-fonts/Vazirmatn-{Regular,Bold}.woff2` → **200 font/woff2**; CSS served 17650 bytes with absolute paths |
| **B2** login font roboto | CSS forces `--primary-font-family:'Vazirmatn'` + body/input/textarea/select/button on `[dir="rtl"]` | login page renders Persian, font override present 2× in served CSS |
| **B3** translation missing | Full **2906-key** Persian overlay at `custom/Language/fa-IR.ini` (correct path: `APP_ROOT.'/custom/Language/'`, not `app/custom/`) | `parse_ini_file` → 2906 entries; `readIni()` → 2965 keys with `آدرس ایمیل را وارد کنید` |
| overflow | `overflow-x:hidden` on `[dir=rtl] body`, `auto` on kanban/maincontent | in served CSS ✅ |

### Live page-by-page test (real admin login, dir + Persian word count)

| Route | HTTP | Persian words | html |
|---|---|---|---|
| /auth/login | 200 | placeholders `آدرس ایمیل را وارد کنید` / `رمز عبور را وارد کنید` | `<html dir="rtl" lang="fa-IR">` ✅ |
| /dashboard/home | 200 | 99 | `<html dir="rtl" lang="fa-IR">` ✅ |
| /projects/showAll | 200 | 139 | `<html dir="rtl" lang="fa-IR">` ✅ |
| /tickets/showAll | 200 | **1194** | `<html dir="rtl" lang="fa-IR">` ✅ |
| /calendar/showMyCalendar | 200 | 105 | `<html dir="rtl" lang="fa-IR">` ✅ |
| /users/showAll | 200 | 148 | `<html dir="rtl" lang="fa-IR">` ✅ |
| /setting/editCompanySettings | 200 | 305 | `<html dir="rtl" lang="fa-IR">` ✅ |
| /timesheets/showAll | 200 | 207 | `<html dir="rtl" lang="fa-IR">` ✅ |
| /strategy/showBoards | 200 | 325 | `<html dir="rtl" lang="fa-IR">` ✅ |

### Gotchas hit (recorded so they aren't repeated)

1. **INI comment char**: PHP's `parse_ini_file` only accepts `;` comments. A `#` header
   containing `(` made the whole overlay fail to parse silently — the app fell back to
   the shipped English file with no error in logs. Symptom: PHP probe showed translations
   working but HTTP endpoints still returned English.
2. **Overlay path**: `CUSTOM_LANG_FOLDER = APP_ROOT.'/custom/Language/'` — the overlay
   belongs at `/var/www/html/custom/Language/`, NOT `/var/www/html/app/custom/Language/`.
3. **Cache layers**: clearing `storage/framework/cache/installation/data/*` alone was not
   enough. Full clear = `cache:clear` + purge `storage/framework/cache/*` and
   `storage/framework/views/*`, then restart php-fpm (opcache `revalidate_freq=60`).
4. **Subagent delegation for bulk translation is unreliable** — 3 of 4 translation
   subagents stalled for ~50 minutes reading the input file repeatedly instead of
   writing. Translating inline via a generated dict was both faster and verifiable.

## Rollback (verified artifacts)

Pre-change backup at server `/root/lt-backup-pre-p0/`:
`lt-full-2026-10-09-1144.sql.gz` (DB), `files-and-lang.tgz` (theme CSS + fonts + Language),
`docker-compose.yml`.

```bash
# Revert translation overlay (app returns to shipped fa-IR.ini)
docker exec code-leantime-1 rm /var/www/html/custom/Language/fa-IR.ini
# Revert CSS (restores stock Leantime styling + broken font path)
docker cp /root/lt-backup-pre-p0/theme-css/custom.min.css code-leantime-1:/var/www/html/public/theme/default/css/custom.min.css
# Clear cache
docker exec code-leantime-1 sh -c "rm -rf /var/www/html/storage/framework/cache/* /var/www/html/storage/framework/views/*"
# Full DB restore if needed
docker cp /root/lt-backup-pre-p0/lt-full-*.sql.gz code-db-1:/tmp/ && docker exec code-db-1 sh -c "zcat /tmp/lt-full-*.sql.gz | mariadb -uleantime -p995ec6c230c962a3888074dfd21730ce leantime"
```

## Commit

`2ddb692f1bf7ce1b0782addef3214d4a2e82d231` — pushed to `main` on
`h4z4rd95/leantime-persian-rtl`
(https://github.com/h4z4rd95/leantime-persian-rtl/commit/2ddb692f1bf7ce1b0782addef3214d4a2e82d231)

