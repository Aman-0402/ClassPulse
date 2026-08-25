# Deploying to shared cPanel hosting

This app was built with Django Channels (WebSocket) for real-time updates, but
shared cPanel hosting only runs Passenger in WSGI mode — no ASGI, no
long-lived WebSocket connections, and usually no Redis. Real-time features
were removed (2026-08-14) specifically so this app can run on shared cPanel:
the teacher's live attendance screen now polls the REST API every 3 seconds
instead of holding a WebSocket open. Everything below assumes that WSGI-only
version — do not reintroduce Channels without re-checking this file.

## Version control

- Remote: `https://github.com/Aman-0402/ClassPulse.git`, single `main` branch.
- CI: `.github/workflows/ci.yml` runs backend tests (against a real MySQL
  service container) and a frontend typecheck+build on every push/PR to `main`.
  Treat a red CI run as blocking — don't deploy off a commit that failed it.

## Backend (Django) — cPanel "Setup Python App" + Git Version Control

1. **Setup Python App** (cPanel UI): create an app, Python 3.10+, application
   root e.g. `classpulse-backend`, application URL e.g. `api.yourdomain.com`
   or `yourdomain.com/api`. cPanel creates a virtualenv and a
   `passenger_wsgi.py` stub — point it at `classpulse.wsgi.application`
   (the file already exists at `backend/classpulse/wsgi.py`).
2. **Environment variables**: cPanel's Python App UI has an "Environment
   Variables" section — set `SECRET_KEY` (generate a real one, never reuse
   the dev key), `DEBUG=False`, `ALLOWED_HOSTS` (your domain), `DB_NAME`,
   `DB_USER`, `DB_PASSWORD`, `DB_HOST` (usually `localhost`), `DB_PORT`
   (usually `3306`), `CORS_ALLOWED_ORIGINS` (your frontend's origin, e.g.
   `https://yourdomain.com`). These are read by `backend/classpulse/settings.py`
   via `python-dotenv` — no `.env` file needed if set here, but a `.env` in
   the app root works too and is gitignored so it's safe to hand-create on
   the server. Never rely on the insecure dev-only fallback values.
3. **Database**: create a MySQL database + user in cPanel's "MySQL® Databases"
   tool, matching the env vars above.
4. **Git Version Control** (cPanel UI): add this GitHub repo as a remote,
   clone/pull it into a working copy, then use "Update from Remote" +
   "Deploy HEAD Commit". That runs `.cpanel.yml` at the repo root, which
   copies `backend/` into the app's deploy path, installs requirements,
   runs migrations, runs `collectstatic`, and touches `tmp/restart.txt` to
   make Passenger reload the app.
   - **Edit `.cpanel.yml` first**: replace every `USERNAME` placeholder and
     the `DEPLOYPATH`/virtualenv path with your actual cPanel username and
     the paths cPanel's Setup Python App screen shows you.
5. Re-run "Deploy HEAD Commit" after every push to `main` you want live.
   Some cPanel/WHM setups support a webhook to automate this trigger from
   GitHub — check with your host; if unavailable, this step stays manual.

## Frontend (React/Vite) — static files, deployed separately

Shared cPanel has no Node runtime, so the frontend can't be built on the
server. It's built by GitHub Actions and uploaded as static files instead:

1. Point a subdomain (e.g. the main domain, or `app.yourdomain.com`) at a
   directory in cPanel, e.g. `public_html` or `public_html/app`.
2. Create an FTP/SFTP account for that directory in cPanel's "FTP Accounts".
3. In the GitHub repo, add these under **Settings > Secrets and variables >
   Actions**:
   - Secrets: `CPANEL_FTP_SERVER`, `CPANEL_FTP_USERNAME`, `CPANEL_FTP_PASSWORD`,
     `CPANEL_FTP_REMOTE_DIR` (e.g. `/public_html/`).
   - Variables: `CPANEL_DEPLOY_ENABLED` = `true` (this is the on/off switch —
     the `deploy-frontend` job in `ci.yml` is a no-op until this is set,
     so nothing tries to deploy to a host that isn't configured yet).
4. Before the first real deploy, update `frontend/src/api/client.ts`'s
   `BASE_URL` (currently hardcoded to `http://localhost:8000/api`) to your
   real backend URL — it needs to change per environment eventually; for now,
   edit it before deploying to production and revert for local dev.
5. Once configured, every push to `main` that passes CI automatically builds
   the frontend and FTP-uploads `dist/` to the configured directory.

## What's intentionally not automated

- Backend deploy still needs a manual click in cPanel's Git Version Control
  UI (step 5 above) unless your specific host offers a webhook — most shared
  plans don't expose the SSH/API access GitHub Actions would need to trigger
  it directly.
- Media uploads (student photos) live on the server's filesystem
  (`MEDIA_ROOT`) — back these up separately; they aren't part of git or CI.
