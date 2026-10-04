# Leantime Persian RTL — Deployment Guide

## Quick Facts

| Item | Value |
|---|---|
| Target | `https://leantime.ppsj.ir` (Leantime v3.10.0) |
| Host | Hetzner CX (`65.109.204.200`), Dokploy/Docker |
| Image | `leantime/leantime:latest` → **pin to `3.10.0`** |
| SSH access | `plink -ssh -batch -pw 'kwCqijsJeqmxvncrs9xw%' root@65.109.204.200` |
| DB creds | `/root/.leantime-db-password` (on host) |
| DB container | `leantime-xyopsc-db-1` (mariadb:11) |
| App container | `leantime-xyopsc-leantime-1` |
| Volumes | `leantime-xyopsc_db-data`, `leantime-xyopsc_leantime-files`, `leantime-xyopsc_leantime-public` |
| Font license | **OFL-1.1** (Vazirmatn) — self-host permitted ✅ |
| CSP constraint | `font-src 'self' data: unpkg.com` — fonts must be same-origin |

## What This Package Does

1. **Font**: Downloads Vazirmatn (OFL-1.1) woff2 files and serves them from Leantime's persistent `leantime-public` volume → accessible at `https://leantime.ppsj.ir/userfiles/rtl-fonts/`
2. **RTL CSS**: Injects a `custom.css` file that:
   - Sets Vazirmatn as the global font on `[dir="rtl"]`
   - Flips physical margin-left/right/padding-left/right via `[dir="rtl"]` attribute selectors
   - Reverses float, absolute positioning, text-align, flex direction, arrow icons
   - Handles LTR preservation for URLs, code, dates, technical identifiers
   - Scopes everything to `[dir="rtl"]` so it's inert in LTR mode
3. **Persian locale**: Leantime already ships `fa-IR.ini` with 2284+ translations, `language.direction="rtl"`, and `language.isRTL="true"` — we just set `LEAN_LANGUAGE=fa-IR`

## Deployment Steps

### Step 0: Pre-flight (DO NOT SKIP)

```bash
# 1. Verify we can reach the host
plink -ssh -batch -pw 'kwCqijsJeqmxvncrs9xw%' root@65.109.204.200 "echo OK"

# 2. Check current Leantime version
plink -ssh -batch -pw 'kwCqijsJeqmxvncrs9xw%' root@65.109.204.200 \
  "docker exec leantime-xyopsc-leantime-1 grep -rnoi '3\\.10\\.0' /var/www/html/composer.json 2>/dev/null | head -3"

# 3. Capture .env (for backup)
plink -ssh -batch -pw 'kwCqijsJeqmxvncrs9xw%' root@65.109.204.200 \
  "docker exec leantime-xyopsc-leantime-1 cat /var/www/html/config/.env"
```

### Step 1: Backup (required before any change)

```bash
# DB dump
PLINK_CMD="plink -ssh -batch -pw 'kwCqijsJeqmxvncrs9xw%' root@65.109.204.200"
PW=$($PLINK_CMD sh -c 'cat /root/.leantime-db-password')
$PLINK_CMD "docker exec leantime-xyopsc-db-1 mariadb-dump --single-transaction leantime | gzip > /tmp/lt-backup-$(date +%F).sql.gz"
$PLINK_CMD "docker cp leantime-xyopsc-db-1:/tmp/lt-backup-$(date +%F).sql.gz /tmp/"

# File volumes
$PLINK_CMD "tar czf /tmp/lt-files-$(date +%F).tar.gz -C /var/lib/docker/volumes leantime-xyopsc_leantime-files leantime-xyopsc_leantime-public"

# Download local
scp root@65.109.204.200:/tmp/lt-backup-*.sql.gz ./
scp root@65.109.204.200:/tmp/lt-files-*.tar.gz ./
```

### Step 2: Pin Leantime image tag

In Dokploy UI: Leantime service → edit → change image from `leantime/leantime:latest` to `leantime/leantime:3.10.0`

Or via Dokploy API if available. This prevents floating-`latest` from pulling an incompatible version during our deployment window.

### Step 3: Upload Vazirmatn fonts

```bash
# Create font directory on the persistent public volume
plink -ssh -batch -pw 'kwCqijsJeqmxvncrs9xw%' root@65.109.204.200 \
  "docker exec leantime-xyopsc-leantime-1 mkdir -p /var/www/html/public/userfiles/rtl-fonts && chown www-data:www-data /var/www/html/public/userfiles/rtl-fonts"

# Upload font files (from this repo: leantime-persian-rtl/fonts/)
scp fonts/Vazirmatn-Regular.woff2 fonts/Vazirmatn-Medium.woff2 fonts/Vazirmatn-SemiBold.woff2 fonts/Vazirmatn-Bold.woff2 \
  root@65.109.204.200:/tmp/

plink -ssh -batch -pw 'kwCqijsJeqmxvncrs9xw%' root@65.109.204.200 \
  "docker cp /tmp/Vazirmatn-Regular.woff2 leantime-xyopsc-leantime-1:/var/www/html/public/userfiles/rtl-fonts/ && \
   docker cp /tmp/Vazirmatn-Medium.woff2 leantime-xyopsc-leantime-1:/var/www/html/public/userfiles/rtl-fonts/ && \
   docker cp /tmp/Vazirmatn-SemiBold.woff2 leantime-xyopsc-leantime-1:/var/www/html/public/userfiles/rtl-fonts/ && \
   docker cp /tmp/Vazirmatn-Bold.woff2 leantime-xyopsc-leantime-1:/var/www/html/public/userfiles/rtl-fonts/ && \
   docker exec leantime-xyopsc-leantime-1 chown -R www-data:www-data /var/www/html/public/userfiles/rtl-fonts"

# Verify fonts are accessible via URL
curl -sI "https://leantime.ppsj.ir/userfiles/rtl-fonts/Vazirmatn-Regular.woff2" | head -5
```

Expected: `HTTP/2 200` and `Content-Type: application/font-woff2`

### Step 4: Upload RTL CSS (upgrade-safe via Theme custom.css)

Leantime's `Theme::getCustomStyleUrl()` loads `public/theme/<active>/css/custom.min.css` (preferred) or `public/theme/<active>/css/custom.css` **after** the theme stylesheet. The default theme is `default`. If neither file exists the `<link>` is omitted entirely, so there is no empty-href risk while the file is absent.

**Note:** `getAssetPath()` checks `custom.min.css` FIRST — use that filename so it wins deterministically.

```bash
# Create the custom.css path in the default theme
plink -ssh -batch -pw 'kwCqijsJeqmxvncrs9xw%' root@65.109.204.200 \
  "docker exec leantime-xyopsc-leantime-1 mkdir -p /var/www/html/public/theme/default/css && \
   docker exec leantime-xyopsc-leantime-1 chown www-data:www-data /var/www/html/public/theme/default/css"

# Upload custom-rtl.css (combined + font URL updated)
scp css/shared-rtl-foundation.css root@65.109.204.200:/tmp/custom-rtl.css

# Modify font paths for the container environment
plink -ssh -batch -pw 'kwCqijsJeqmxvncrs9xw%' root@65.109.204.200 \
  "sed 's|url(\"fonts/|url(\"/userfiles/rtl-fonts/|g' /tmp/custom-rtl.css > /tmp/custom-rtl-final.css && \
   docker cp /tmp/custom-rtl-final.css leantime-xyopsc-leantime-1:/var/www/html/public/theme/default/css/custom.min.css && \
   docker exec leantime-xyopsc-leantime-1 chown www-data:www-data /var/www/html/public/theme/default/css/custom.min.css"

# Verify
plink -ssh -batch -pw 'kwCqijsJeqmxvncrs9xw%' root@65.109.204.200 \
  "docker exec leantime-xyopsc-leantime-1 wc -l /var/www/html/public/theme/default/css/custom.min.css"
```

### Step 5: Set Persian as default language

Set `LEAN_LANGUAGE=fa-IR` in the Leantime service environment variables via Dokploy.

```bash
# Verify current setting
plink -ssh -batch -pw 'kwCqijsJeqmxvncrs9xw%' root@65.109.204.200 \
  "docker exec leantime-xyopsc-db-1 sh -c 'PW=\$(cat /root/.leantime-db-password) && mariadb -uleantime -p\"\\$PW\" leantime -N -e \"SELECT \\`key\\`, LEFT(\\`value\\`,80) FROM zp_settings WHERE \\`key\\` LIKE \\\"language\\\" OR \\`key\\` LIKE \\\"companysettings.language\\\" LIMIT 10\"'"
```

Set via Dokploy UI: Leantime service → Environment Variables → add `LEAN_LANGUAGE=fa-IR`

Or via command:
```bash
plink -ssh -batch -pw 'kwCqijsJeqmxvncrs9xw%' root@65.109.204.200 \
  "docker exec leantime-xyopsc-leantime-1 sh -c 'echo LEAN_LANGUAGE=fa-IR >> /var/www/html/config/.env'"
```

### Step 6: Verify

```bash
# 1. Check login page HTML has dir="rtl"
curl -sI "https://leantime.ppsj.ir/auth/login" | grep -i "location"
curl -sL "https://leantime.ppsj.ir/auth/login" | grep -o '<html[^>]*>'

# Expected: <html dir="rtl" lang="fa-IR">

# 2. Check custom.css is loaded (in page source, should appear after theme CSS)
curl -sL "https://leantime.ppsj.ir/auth/login" | grep -o 'theme.*custom\\.css'

# 3. Check font is served
curl -sI "https://leantime.ppsj.ir/userfiles/rtl-fonts/Vazirmatn-Regular.woff2"

# 4. Check i18n endpoint returns RTL values
curl -sL "https://leantime.ppsj.ir/api/i18n?v=3.10.0" | grep -o 'direction[^,]*' | head -2
curl -sL "https://leantime.ppsj.ir/api/i18n?v=3.10.0" | grep -o 'isRTL[^,]*' | head -2

# 5. Check a dashboard page
curl -sL "https://leantime.ppsj.ir/dashboard/home" | grep -o '<html[^>]*>'
```

## Rollback Plan (30 seconds)

If anything breaks, revert immediately:

```bash
# 1. Remove custom.min.css (Leantime reverts to stock styling)
plink -ssh -batch -pw 'kwCqijsJeqmxvncrs9xw%' root@65.109.204.200 \
  "docker exec leantime-xyopsc-leantime-1 rm /var/www/html/public/theme/default/css/custom.min.css"

# 2. Revert language to English
plink -ssh -batch -pw 'kwCqijsJeqmxvncrs9xw%' root@65.109.204.200 \
  "docker exec leantime-xyopsc-leantime-1 sh -c 'echo LEAN_LANGUAGE=en-US >> /var/www/html/config/.env'"

# 3. Revert image tag to latest (via Dokploy UI)
# Dokploy → Leantime service → change image from 3.10.0 back to latest → Deploy

# 4. If DB state corrupted: restore from backup
plink -ssh -batch -pw 'kwCqijsJeqmxvncrs9xw%' root@65.109.204.200 \
  "docker cp /tmp/lt-backup-*.sql.gz leantime-xyopsc-db-1:/tmp/ && \
   docker exec leantime-xyopsc-db-1 sh -c 'zcat /tmp/lt-backup-*.sql.gz | mariadb leantime'"
```

## Upgrade Strategy (future Leantime updates)

When Leantime releases a new version:

1. **Read changelog** — check for breaking changes (historically: 3.6.0/3.6.1, 3.2)
2. **Backup** — DB dump + file volumes + `.env` (per § Step 0)
3. **Update image tag** in Dokploy
4. **Re-verify**: login, one API call, check `<html dir=...>` still outputs correctly
5. **Re-check custom.css**: if Leantime changed the Theme.php `getCustomStyleUrl()` path or the order of CSS loading, update accordingly
6. **Re-run prototype screens** — if visual breaks, update selectors in `shared-rtl-foundation.css`

The `[dir="rtl"]` scoping means custom.css is 100% inert in LTR mode, so a broken Leantime upgrade that doesn't change `language.direction` won't trigger any of our rules.

## What's NOT Covered (known limitations)

| Area | Status | Notes |
|---|---|---|
| Inline date formatting | PARTIAL | JS datepicker uses `moment.js` — Persian digits (۰۱۲۳) need Moment locale `fa` |
| Persian digit conversion (0-9 → ۰-۹) | NOT IN SCOPE | Would need a small JS module; CSS `font-feature-settings` doesn't convert digits |
| Third-party widget RTL (Uppy, JSTree, Shepherd) | PARTIAL | Shipped vendor CSS has basic RTL selectors; our `[dir="rtl"]` rules don't override them |
| Calendar/Gantt visual direction | PARTIAL | CSS `flex-direction: row-reverse` applied; actual SVG arrow/icon flipping depends on specific component |
| Keyboard input method (Arabic/Persian keyboard layout) | NOT IN SCOPE | Client-side, not server-side |
| RTL for mobile-specific layout | PARTIAL | Mobile breakpoints use `display:none` on `.regLeft` — no RTL-specific mobile changes needed |

## Screenshots

Run the prototype screens locally in a browser:
- `prototype/screens/login.html` — Login page (Persian RTL)
- `prototype/screens/dashboard.html` — Project dashboard + kanban (Persian RTL)
- `prototype/screens/task-detail.html` — Task detail view (Persian RTL)

Then deploy to production and screenshot key screens for the acceptance criteria.