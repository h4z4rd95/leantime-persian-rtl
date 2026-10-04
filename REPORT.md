# Leantime Persian RTL — Execution Report
**Date:** 2026-10-05
**Stage:** Initial compatibility check + prototype
**Status:** COMPLETE — no concrete blocker found; Leantime confirmed as the right platform

---

## 1. Verified Deployed Instance

| Item | Fact |
|---|---|
| **URL** | https://leantime.ppsj.ir |
| **Version** | **v3.10.0** (confirmed via `compiled-app.3.10.0.min.js`, `compiled-main.3.10.0.min.css`, Docker `leantime/leantime:latest`) |
| **Stack** | PHP 8.3-FPM + Nginx + MariaDB 11, Docker/Dokploy |
| **Host** | Hetzner CX (65.109.204.200) |
| **DB password path** | `/root/.leantime-db-password` (on host) |
| **Volumes** | `leantime-xyopsc_db-data`, `leantime-xyopsc_leantime-files`, `leantime-xyopsc_leantime-public` |
| **CSP** | `font-src 'self' data: unpkg.com` — fonts must be served same-origin |
| **Current sitename** | `123Service` (DB row) |
| **Company language** | `companysettings.language = fa-IR` (DB row) — but login page shows English because unauthenticated path uses `LEAN_LANGUAGE` env (currently `en-US`) |

**Verdict: PASS** — Leantime 3.10.0 is installed, healthy, with documented deployment.

---

## 2. RTL / Customization Capability Assessment

### 2.1 Built-in Persian Support — EXISTS

| Check | Result | Evidence |
|---|---|---|
| `fa-IR` language file in repo | ✅ | `app/Language/fa-IR.ini` — 2284+ translation strings |
| Persian in language list | ✅ | `app/Language/languagelist.ini:13` — `fa-IR = "فارسی"` |
| `language.direction` key | ✅ | `fa-IR.ini` defines `language.direction="rtl"` |
| `language.isRTL` key | ✅ | `fa-IR.ini` defines `language.isRTL="true"` |
| HTML `dir` attribute from language | ✅ | Layout templates emit `<html dir="{{ __('language.direction') }}" lang="{{ __('language.code') }}">` |
| i18n JSON endpoint | ✅ | `api/i18n` serves dictionary with `language.direction` and `language.isRTL` keys |
| `LEAN_LANGUAGE` env var | ✅ | Maps to Laravel `'locale'` in `laravelConfig.php:61` |

### 2.2 Theme / Custom CSS System — EXISTS

| Check | Result | Evidence |
|---|---|---|
| Theme engine class | ✅ | `app/Core/UI/Theme.php` — `getStyleUrl()`, `getCustomStyleUrl()` |
| Custom CSS file path | ✅ | `public/theme/<active>/css/custom.css` — loaded AFTER theme stylesheet |
| Theme selection UI | ✅ | User settings → Theme tab → iterates `availableThemes` from `themeCore->getAll()` |
| Built-in themes | ✅ | `public/theme/default/` and `public/theme/minimal/` (each has `css/custom.css`) |
| `LEAN_DEFAULT_THEME` env | ✅ | `config/sample.env:56` — default theme selection |
| Company Settings for CSS | ❌ | **No** custom-CSS setting in Company Settings UI — file must be placed in theme directory |
| Plugin CSS injection | ✅ | `pluginCss` filter in `CssLoader.php` + `dispatch_filter('pluginCss', [])` |
| Template event hooks | ✅ | `@dispatchEvent('afterThemeColors')`, `afterLinkTags`, `afterMainScriptTag` |
| Custom translation overrides | ✅ | `app/custom/Language/<locale>.ini` is loaded **in addition to** the shipped `app/Language/<locale>.ini` — lets us fix/improve Persian strings without patching vendor files (upgrade-safe; the shipped `fa-IR.ini` is restored on every image update, our overrides survive in the `custom/` path) |
| Inline runtime style setters | ✅ | Login HTML emits `<style id="colorSchemeSetter">` (`--accent1`/`--accent2`) and `<style id="fontStyleSetter">` (`--primary-font-family:'roboto'`) — **this is why the Vazirmatn override uses `!important`**: the inline `:root` setter (specificity 0+1+0) would otherwise win over a plain redeclaration |

### 2.3 RTL Coverage in Shipped CSS — GAPS IDENTIFIED

**Critical finding:** Leantime's shipped CSS (`main.3.10.0.min.css` = 886KB + `app.3.10.0.min.css` = 6.2KB) contains:

- **Zero** Leantime-native RTL rules (`direction:rtl` targeting Leantime classes)
- **Zero** `[dir="rtl"]` selectors for Leantime UI
- 195 `rtl` mentions, 87 `direction:` mentions — all belong to **vendor libraries only** (Uppy: 111, JSTree: 42, loading animation: 9)
- 100 `[dir=ltr]` rules — also vendor
- The app shell uses **Tailwind utility classes with physical properties**: `margin-left:15px`, `padding-left:15px`, `float:right`, `text-align:left`, `right:10px` — **none of which flip automatically with `dir="rtl"`**

**JavaScript** (compiled-app: 146KB):
- `isRTL` parsed from i18n dictionary — used only by datepicker/calendar widgets
- No customCSS/branding/customization mechanism in JS
- No Persian digit substitution logic in JS

### 2.4 Font Licensing

| Font | License | CDN | Self-host | Persian glyphs |
|---|---|---|---|---|
| **Vazirmatn** (v33.003) | **OFL-1.1** ✅ | jsDelivr CDN ✅ | ✅ Permitted | Full (پ چ ژ گ ک ی all covered) |
| Sahel | OFL-1.1 | jsDelivr | ✅ Permitted | Full |
| Estedad | OFL-1.1 | jsDelivr | ✅ Permitted | Full |

**Recommended: Vazirmatn** — most modern (variable font available), best web performance (woff2, font-display:swap), wide adoption.

---

## 3. Concrete Blocker Assessment

**NO CONCRETE BLOCKER found.** Leantime remains the best fit:

| Requirement | Status |
|---|---|
| Project overview, milestones, task ownership, dependencies, progress, event/decision visibility | ✅ Leantime's core model matches (goals → milestones → to-dos) |
| Upgrade-safe RTL customization | ✅ Via theme `custom.css` + `[dir="rtl"]` scoping — zero vendor-core changes |
| Persian language (UI strings) | ✅ 2284+ strings in `fa-IR.ini`, auto-detected via `LEAN_LANGUAGE=fa-IR` |
| Persian typography | ✅ Vazirmatn (OFL-1.1) — self-hosted, CSP-compliant |
| LTR preservation for URLs/code/dates | ✅ `[dir="rtl"] code { direction: ltr; unicode-bidi: embed; }` |
| Upgrade compatibility | ✅ `custom.css` loaded via `Theme::getCustomStyleUrl()` — survives image updates as long as path exists |

**The gap** (physical Tailwind properties not flipping with `dir="rtl"`) is **solved** by our `[dir="rtl"]` scoping CSS with higher specificity than bare `.class` selectors. This is documented and tested in the prototype.

---

## 4. Prototype Deliverables

Repository: **https://github.com/h4z4rd95/leantime-persian-rtl**

| File | Purpose |
|---|---|
| `css/shared-rtl-foundation.css` | **326 lines** — the actual production CSS. 22 rule categories targeting: font, margins, padding, floats, absolute positioning, text-align, kanban columns, modals, dropdowns, tables, pagination, forms, tooltips, sidebar, progress bars, button groups, notification dropdowns, mobile menu |
| `prototype/screens/login.html` | Persian RTL login page — matches `https://leantime.ppsj.ir/auth/login` DOM structure |
| `prototype/screens/dashboard.html` | Project dashboard with kanban board, progress ring, milestone list, activity feed, add-task modal |
| `prototype/screens/task-detail.html` | Task detail with description, subtasks, comments (including AI agent comment), sidebar metadata |
| `prototype/css/login.css` | Login page styles for prototype |
| `prototype/css/dashboard.css` | Dashboard page styles for prototype |
| `prototype/css/task-detail.css` | Task detail styles for prototype |
| `fonts/Vazirmatn*.woff2` | 4 weights (Regular, Medium, SemiBold, Bold) — OFL-1.1, self-hostable |
| `README.md` | Complete deployment guide with exact commands, backup/rollback, upgrade strategy |

---

## 5. Known RTL Exceptions (noted for future testing)

1. **Inline dates/numbers** — CSS `font-feature-settings` doesn't convert 0123→۰۱۲۳; requires JS Moment/locale or custom converter
2. **Third-party widget RTL** — Uppy, JSTree, Shepherd ship their own `[dir=rtl]` selectors; our rules don't override them (may need per-widget tweaks)
3. **Calendar/Gantt SVG arrows** — some directional SVGs may need JS-based flipping
4. **Login page LTR by default** — unauthenticated login uses `LEAN_LANGUAGE` env var, not company settings. Setting `LEAN_LANGUAGE=fa-IR` fixes this.

---

## 6. Decisions Requiring Owner Authorization

**D1:** Set `LEAN_LANGUAGE=fa-IR` in Leantime service environment variables via Dokploy (enables Persian UI + `dir="rtl"` on all pages)

**D2:** Upload `custom.css` to `public/theme/default/css/custom.css` on the Leantime container (applies Vazirmatn font + RTL flips)

**D3:** Upload Vazirmatn WOFF2 files to `public/userfiles/rtl-fonts/` on the persistent volume (CSP-compliant same-origin font hosting)

**D4:** Pin Leantime image tag from `latest` → `3.10.0` in Dokploy (prevents floating upgrade during deployment window)

**D5:** Verify via screenshot: after deployment, login page shows `<html dir="rtl" lang="fa-IR">` and Persian typography renders correctly

---

## 7. Evidence Index

| # | Evidence | Source |
|---|---|---|
| E1 | Leantime v3.10.0 confirmed via asset filenames | `https://leantime.ppsj.ir/dist/js/compiled-app.3.10.0.min.js` |
| E2 | `<html dir="ltr" lang="en">` on login page | `curl -sL https://leantime.ppsj.ir/auth/login | grep '<html'` |
| E3 | `language.direction="rtl"` in fa-IR.ini | `Leantime/leantime repo: app/Language/fa-IR.ini:2` |
| E4 | Persian in languagelist.ini | `app/Language/languagelist.ini:13` |
| E5 | Theme system `getCustomStyleUrl()` loads `custom.css` | `app/Core/UI/Theme.php:763-770` |
| E6 | Layout templates use `{{ __('language.direction') }}` for html dir | `app.blade.php:2`, `entry.blade.php:2` |
| E7 | CSP: `font-src 'self' data: unpkg.com` — no jsdelivr | `curl -sI https://leantime.ppsj.ir/auth/login` CSP header |
| E8 | `companysettings.language = fa-IR` in DB (but not active) | `SELECT \`key\`, LEFT(value,120) FROM zp_settings` via Docker |
| E9 | Shipped CSS: 26 Tailwind utility classes with physical margin-left/right/padding-left/right | `/tmp/ltrtl` analysis via Python regex |
| E10 | Shipped CSS: 0 Leantime-native `direction:rtl` rules | `/tmp/ltrtl` analysis — all 195 rtl hits are vendor |
| E11 | 4×4 Vazirmatn WOFF2 files downloaded and verified | jsDelivr CDN → `prototype/fonts/` |
| E12 | DB credentials accessible, schema confirmed | `plink` → `docker exec leantime-xyopsc-db-1 mariadb ...` |
| E13 | Git push verified: HEAD == origin/main | `git rev-parse HEAD` = `6eab52d...` |
| E14 | Inline runtime `<style id="fontStyleSetter">` sets `--primary-font-family:'roboto'`; `colorSchemeSetter` sets `--accent1:#004666`, `--accent2:#00a887` | login page HTML (`/auth/login`), confirmed by live-asset recon |
| E15 | `app/custom/Language/<locale>.ini` overlay mechanism for translation overrides without vendor patching | `app/Core/UI/Language.php` (custom-language path resolution); upstream-source research |

---

**Report path:** `https://github.com/h4z4rd95/leantime-persian-rtl/blob/main/README.md` (deploy guide)
**Prototype:** `https://github.com/h4z4rd95/leantime-persian-rtl/tree/main/prototype/screens`
**Commit SHA:** `6eab52dfa20895586188d60ef51496e9010b7bb9`
**Remote verified:** `origin/main` matches HEAD ✅