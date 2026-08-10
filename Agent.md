# Agent.md — ClassPulse

Instructions for any coding agent (Claude, Copilot, etc.) working in this repo.

## What this is

Smart QR-Based Real-Time Attendance System. Full spec: [`document.md`](document.md). Phase-by-phase build plan: [`docs/plan.md`](docs/plan.md).

## Tech Stack

Decoupled: Django backend (API + WebSocket only, no server-rendered templates) + separate React SPA frontend.

- **Backend:** Python 3.12, Django, Django REST Framework, Django Channels (WebSocket)
- **DB:** SQLite (dev), PostgreSQL (prod)
- **Frontend:** React + TypeScript or JS, Bootstrap 5 (via `react-bootstrap` or plain Bootstrap CSS), a browser QR-scanner library (e.g. `html5-qrcode`), fetch/axios for REST, native `WebSocket` for the live dashboard
- **Async/QR rotation:** Channels + a periodic task (APScheduler or Celery beat) generating a new `QRToken` every 15s per active session
- **Exports:** `openpyxl` (XLSX), stdlib `csv`, `reportlab`/`weasyprint` (PDF)

## Project Structure (target)

```text
classpulse/
├── backend/
│   ├── manage.py
│   ├── classpulse/       # Django project settings, asgi.py, urls.py
│   ├── accounts/          # Student, Teacher models + auth
│   ├── attendance/         # AttendanceSession, QRToken, Attendance, ActivityLog
│   ├── realtime/            # Channels consumers/routing
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/          # student/, teacher/ views
│   │   ├── components/
│   │   ├── api/             # REST + WebSocket client
│   │   └── App.tsx
│   └── package.json
└── docs/plan.md
```

## Build Order

Follow `docs/plan.md` phases in order (1 → 5). Do not start a phase until the previous phase's exit criteria are met. Each phase is independently demoable.

## Non-Negotiable Rules

1. **Server is the source of truth for QR validity.** The client never decides whether a scan is valid — see doc.md §18/§34. All checks in doc.md §10's validation chain happen in the backend.
2. **Passwords:** never store plaintext. Use Django's built-in password hashing.
3. **Duplicate attendance:** enforce with a DB unique constraint on `(student_id, session_id)`, not application logic alone.
4. **Unique CRN:** enforce with a DB unique constraint, not application logic alone.
5. **QR payload:** an opaque random token only — no student data, no session internals.
6. **No secrets committed.** `DATABASE_URL`, `SECRET_KEY`, etc. go in `.env` / environment, never in code.
7. **CORS/CSRF:** backend is a pure API for a separately-hosted SPA — configure `django-cors-headers` for the frontend origin, use token/session auth appropriately, never disable CSRF protection wholesale.

## Commands (once scaffolded)

```bash
# backend
cd backend
python -m venv venv
venv\Scripts\activate        # Windows (PowerShell)
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# frontend
cd frontend
npm install
npm run dev
```

## Conventions

- One Django app per bounded concern (`accounts`, `attendance`, `realtime`) — don't dump everything into one app.
- DRF serializers for all API I/O; validate at the serializer/model layer, not just in views.
- Keep WebSocket consumer logic thin — business logic (validation chain, marking attendance) lives in `attendance/services.py` or similar, callable from both the REST view and the consumer.
- Every new model needs an admin registration for manual inspection during dev.
- Frontend calls backend only through `frontend/src/api/` — no inline `fetch`/`axios` calls scattered in components.
- Bootstrap for layout/components; avoid mixing in another CSS framework.

## Out of Scope (v1)

Multiple subjects/teachers, timetable integration, geofencing, face/device verification, mobile app. See doc.md §4 and §33 for the full future-enhancement list — don't build these ahead of being asked.

## Work Log

Every phase/work update gets an entry here, newest first.

- **2026-08-10** — Phase 1 Task 1 done: Django backend scaffolded (`backend/classpulse`, `backend/accounts`), DRF token auth + CORS + media settings wired. Spec + code-quality reviewed, approved. Added root `.gitignore`.
- **2026-08-10** — Wrote detailed Phase 1 (Auth) implementation plan: `docs/superpowers/plans/2026-08-10-phase-1-auth.md`. TDD task-by-task, backend (Django+DRF token auth) and frontend (React+Bootstrap). Not yet executed.
- **2026-08-10** — Stack finalized: decoupled Django REST/Channels backend + React+Bootstrap frontend (`backend/` + `frontend/`). Updated `Agent.md`, `docs/plan.md`, `Readme.md`.
- **2026-08-10** — Repo initialized. Wrote `document.md` spec (pre-existing), `docs/plan.md` (5-phase plan), `Agent.md`, `Readme.md`. No code yet.
