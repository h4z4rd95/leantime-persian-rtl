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

## Fix plan

1. **B1**: rebuild `custom.min.css` with absolute font paths `/userfiles/rtl-fonts/...`
   (or copy fonts to `/public/theme/default/fonts/`).
2. **B2**: force `--primary-font-family: 'Vazirmatn'` for the login/unauthenticated path
   (CSS override with high specificity in custom.min.css, since we can't set usersettings for anon).
3. **B3**: build a complete Persian translation via the upgrade-safe overlay
   `app/custom/Language/fa-IR.ini` (loaded after the shipped file per `Language.php:readIni`),
   covering all 2170+ shipped keys + the 636 missing ones. Then clear the
   `languages.lang_fa-IR` cache so it takes effect.
4. Backup DB + files before any change; test login + dashboard after; push to repo.
