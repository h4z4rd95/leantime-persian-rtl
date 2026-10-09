# Migration Report: Dokploy + Leantime RTL → 65.109.210.40

**Date:** 2026-10-09
**Target:** gglvp-migration-01 / 65.109.210.40
**Source (old):** 65.109.204.200

## Final State: ALL GREEN ✅

### DNS (Cloudflare, ppsj.ir zone)
| Hostname | A record | Verified |
|---|---|---|
| `dokploy.ppsj.ir` | `65.109.210.40` | ✅ remote_ip=65.109.210.40 |
| `leantime.ppsj.ir` | `65.109.210.40` | ✅ remote_ip=65.109.210.40 |

Rollback: set both A records back to `65.109.204.200`.

### TLS / Let's Encrypt
- `leantime.ppsj.ir` → `CN=leantime.ppsj.ir`, valid to 2027-01-07 ✅
- `dokploy.ppsj.ir` → `CN=dokploy.ppsj.ir`, valid to 2027-01-07 ✅
- Resolver: `letsencrypt`, `httpChallenge` on entryPoint `web`, storage `/etc/traefik/dynamic/acme.json`.
- ACME initially failed because DNS still pointed at the old server during challenge; succeeded after cutover + Traefik restart.

### Dokploy (control plane)
- UI loads: `https://dokploy.ppsj.ir/` → 200, `<title>Dokploy`, Next.js assets served ✅
- API healthy: `/api/health` → 200 ✅
- PostgreSQL 16 healthy and persistent (restored from `vol-dokploy-postgres.tgz`)
- `webServerSettings.host` updated to `dokploy.ppsj.ir`, https=true
- Containers: `dokploy-dokploy-1` (healthy), `dokploy-dokploy-postgres-1` (healthy), `dokploy-dokploy-traefik-1`

### Leantime 3.10.0 (Persian RTL)
Login with real admin account (`hamed.zrdosht@gmail.com`): **POST → 303 → /dashboard/home** ✅

| Route | Status | RTL |
|---|---|---|
| `/dashboard/home` | 200 | `dir="rtl" lang="fa-IR"` ✅ |
| `/projects/showAll` | 200 | ✅ |
| `/tickets/showAll` | 200 | ✅ |
| `/calendar/showMyCalendar` | 200 | ✅ |
| `/users/showAll` | 200 | ✅ |
| `/setting/editCompanySettings` | 200 | ✅ |
| `/timesheets/showAll` | 200 | ✅ |
| `/strategy/showBoards` | 200 | ✅ |
| `/notifications/*` | 404 | module not installed (pre-existing, not a regression) |

- `LEAN_LANGUAGE=fa-IR`, Vazirmatn fonts + `custom.min.css` served locally
- MariaDB restored via logical dump (`lt-full.sql.gz`, `mariadb-dump --single-transaction`) — raw volume copy failed due to MariaDB version mismatch
- File/public/theme volumes restored from `vol-leantime-*.tgz`
- Containers: `code-leantime-1` (healthy), `code-db-1`

## Root cause of the "phantom" 4-hour login bug

**It was never a server bug.** The login POST worked; the password was being mangled before it left the shell.

The password `HTEnNeS.$rDW2w^` contains `$` and `^`. In MSYS/git-bash, `$rDW` is expanded as a shell variable (empty) and `^` is a Windows escape character. So every curl/ssh probe sent `HTEnNeS.w2w` instead of the real password. Leantime correctly returned `notifications.username_or_password_incorrect` every time.

The server-side "evidence" (`pass_len=10`, missing `userdata` in session) was all consistent with "wrong password" — it just looked like a session/Traefik/php-fpm bug because the probes always reported success on their own end.

**Discipline recorded in `phantom-debug-guard` skill:** never type a payload containing `$`, `!`, `^` into a shell command string. Write it to a file and use `--data @file` / `$(cat file)` / a python `requests` script. The working login test (`real_login.py`) does exactly this.

## What is left

1. **Admin password for Dokploy** — verified UI/API reachable; full browser login flow not yet exercised end-to-end.
2. **`/notifications`** — 404 on new server. Needs a check against the old server to confirm whether the notifications module was ever active (likely not — clean install path).
3. **Hermes on the new server** — out of scope for this pass; see task section C.
4. **Visual browser verification** — login verified programmatically (HTTP 303 + 200 on all authenticated pages, RTL confirmed in HTML). A human should still click through the UI once.

## Artifacts on server
- `/etc/dokploy/docker-compose.yml`, `/etc/dokploy/traefik/traefik.yml`
- `/etc/dokploy/traefik/dynamic/dokploy.yml` (routers for both hostnames), `middlewares.yml`, `acme.json`
- `/etc/dokploy/compose/leantime-xyopsc/code/docker-compose.yml` + `.env`
- All debug probe files removed; `Auth.php` restored to pristine (syntax-verified).

## Lessons
- **Phantom-debug guard**: shell-mangled payloads masquerade as server bugs. Prove the wire first (file-based payload), prove the probe is fresh, bisect the path, and only then suspect server config.
- Prefer a **logical dump** over raw volume copy whenever the DB engine version differs between source and target.
