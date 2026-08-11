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

- **2026-08-11** — Phase 3 Task 2 done: `TokenAuthMiddleware` (WebSocket auth, resolves `?token=` against the existing DRF `authtoken.Token`, sets `scope["user"]`). Code-quality review found deactivated users could still authenticate over WS (no `is_active` check, unlike DRF's own `TokenAuthentication`); fixed with `user__is_active=True` filter. Re-verified directly, approved.
- **2026-08-11** — Phase 3 (Real-Time Dashboard) started. Wrote detailed plan: `docs/superpowers/plans/2026-08-11-phase-3-realtime-dashboard.md` (8 tasks). Task 1 done: Django Channels scaffolded (`daphne`+`channels` in `INSTALLED_APPS`, in-memory channel layer, `asgi.py` rewritten). Spec + code-quality reviewed, approved; added a one-line settings comment on the in-memory layer's single-process constraint per review.
- **2026-08-11** — Phase 2 Task 9 done (final task): student `ScanQRPage` (camera scan via `html5-qrcode`, auto-submits to `markAttendance`), linked from `StudentProfilePage`. Code-quality review found Critical bug (`scanner.stop()` throws synchronously, not via rejected promise, if camera permission was denied — escaped the `.catch()` guard uncaught) plus the same missing-mounted-guard pattern already fixed twice on `LiveQRPage`; fixed with `getState() === SCANNING` check before stop + `active` flag. Re-reviewed, approved. **Phase 2 (Attendance Sessions & QR) complete** — all 9 tasks done, exit criteria met (QR rotates 15s, one scan = one mark, DB-level duplicate prevention, all validation server-side).
- **2026-08-11** — Phase 2 Task 8 done: teacher `StartAttendancePage` + `LiveQRPage` (polls QR every 15s via `qrcode.react`), linked from `TeacherProfilePage`. Code-quality review found two Critical bugs repeating a Phase-1-fixed pattern (unhandled poll failure → stuck spinner forever; unhandled stop failure → button silently no-ops) — fixed with error state + unconditional navigate-on-stop. Re-review caught a third bug in the fix itself (error state never cleared on recovery, permanently hiding QR after one transient blip) — fixed with `setError(null)` on successful poll. Verified directly, approved.
- **2026-08-11** — Phase 2 Task 7 done: frontend API client extended (`startSession`, `stopSession`, `getSessionQR`, `markAttendance`). Verified directly (exact-match spec, pure append) — no separate review dispatch needed for this mechanical task.
- **2026-08-11** — Phase 2 Task 6 done: attendance models registered in admin. Full backend suite: 35/35 passing. Backend half of Phase 2 complete (Tasks 1-6) — moving to frontend (Tasks 7-9).
- **2026-08-11** — Phase 2 Task 5 done: `POST /api/attendance/mark/` — core feature, full server-side validation chain (token exists → session active → not expired → not already marked → student role via `IsStudent`), student-only, DB-level `UniqueConstraint` backstop. Code-quality review found Critical bug: unhandled `IntegrityError` under concurrent duplicate-scan race → raw 500 instead of clean 400; fixed with `transaction.atomic()` + `except IntegrityError` in the view. Re-reviewed, approved. Follow-up nice-to-have (not blocking): a mocked test exercising the `except IntegrityError` branch directly, vs. current code-inspection-level confidence — true threading-based race test out of scope.
- **2026-08-11** — Phase 2 Task 4 done: `GET /api/attendance/sessions/<id>/qr/` (teacher-only, ownership-scoped), lazy 15s rotation via `attendance/services.py::get_current_qr_token`. Code-quality review found non-deterministic tie in token ordering (`order_by("-created_at")` alone); fixed with `-id` secondary sort. Confirmed benign, accepted TOCTOU race on concurrent-request duplicate-mint (no security/correctness impact — validation at scan time is fully decoupled from issuance, per `MarkAttendanceSerializer` design in Task 5).
- **2026-08-11** — Phase 2 Task 3 done: teacher-only `POST /api/attendance/sessions/start/` and `.../stop/` (ownership-scoped, other teachers' sessions 404). Code-quality review found repeat-stop-call bug (`end_time` silently overwritten on each call); fixed with an already-closed guard returning 400. Re-reviewed, approved.
- **2026-08-11** — Phase 2 Task 2 done: `attendance` app scaffolded, `AttendanceSession`/`QRToken`/`Attendance` models (DB-level `UniqueConstraint` on student+session). Code-quality review found latent bug (`QRToken.expires_at` NOT NULL but only set in `save()` override — bypassable via bulk_create/full_clean); fixed by switching to `default=` callable, matching the `token` field's existing pattern. Re-reviewed, approved.
- **2026-08-11** — Phase 2 (Attendance Sessions & QR) started. Wrote detailed plan: `docs/superpowers/plans/2026-08-11-phase-2-attendance-qr.md` (9 tasks). Task 1 done: `IsTeacher`/`IsStudent` DRF permission classes (`accounts/permissions.py`) — closes the role-gating gap flagged at end of Phase 1. Spec + code-quality reviewed, approved. Note: permission tests exercise `has_permission` directly rather than through a real DRF request/view cycle — acceptable, integration coverage arrives naturally once Task 3+ wires these into `attendance` views.
- **2026-08-10** — Phase 1 Task 9 done (final task): teacher profile endpoint (`GET /api/teacher/profile/`) + `TeacherProfilePage`, symmetric to student profile. Spec + code-quality reviewed, approved. **Phase 1 (Authentication & Profiles) complete** — all 9 tasks done, exit criteria met (student register/login/profile, teacher login/profile, DB-level unique CRN). Cross-cutting gap flagged for Phase 2: neither profile endpoint checks `request.user.role` — a student token can fetch `/api/teacher/profile/` and vice versa, no error, just wrong-shaped-but-valid data. Not blocking Phase 1, becomes load-bearing once Phase 2 adds teacher-only session endpoints.
- **2026-08-10** — Phase 1 Task 8 done: registration/login/student-profile pages + route guard (`ProtectedRoute`), wired in App.tsx. Code-quality review found unhandled-401 stuck-spinner bug + blank page on unmatched route (teacher login pre-Task-9); fixed (StudentProfilePage now logs out + redirects on fetch failure, added catch-all route → `/login`). Re-reviewed, approved. Remaining minor/non-blocking: RegisterPage's narrow error-message fallback, missing `controlId` on form groups (a11y), no visually-hidden spinner text.
- **2026-08-10** — Phase 1 Task 7 done: frontend API client (`frontend/src/api/client.ts`) — register/login/profile calls, token interceptor. Spec + code-quality reviewed, approved. Notes for later: type responses on `registerStudent`/`getStudentProfile` (currently `any`), move `BASE_URL` to env var before deploy, no server-side token invalidation on logout.
- **2026-08-10** — Phase 1 Task 6 done: React+Vite+TS frontend scaffolded (`frontend/`), Bootstrap 5 + react-bootstrap + react-router-dom + axios installed. Spec + code-quality reviewed, approved. Note: scaffold resolved React 19 (plan said React 18) — non-breaking, watch for API differences in later tasks.
- **2026-08-10** — Phase 1 Task 5 done: student profile endpoint (`GET /api/student/profile/`), admin registration for User+StudentProfile. Spec + code-quality reviewed, approved with follow-ups: (1) `StudentProfile.DoesNotExist` → unhandled 500 if a teacher or profile-less user hits this route, should be 403/404 — fix before frontend relies on it; (2) `photo` serializes as relative path, not absolute URL (no `context=request` passed); (3) mid-file imports in views.py, cosmetic.
- **2026-08-10** — Phase 1 Task 4 done: role-aware token login (`POST /api/student/login/`, returns token+role+username). Spec + code-quality reviewed, approved. Noted for later phase: no logout/token-revocation endpoint, no throttling.
- **2026-08-10** — Phase 1 Task 3 done: student registration endpoint (`POST /api/student/register/`), DB-level unique CRN + username enforced. Spec + code-quality reviewed, approved. Noted for later: response omits `photo` field, minor TOCTOU race on uniqueness checks under concurrent requests (plan-level tradeoff, not blocking).
- **2026-08-10** — Phase 1 Task 2 done: custom `User` model (role field) + `StudentProfile` (unique CRN) in `accounts` app, migration + 3 model tests passing. Spec + code-quality reviewed, approved.
- **2026-08-10** — Phase 1 Task 1 done: Django backend scaffolded (`backend/classpulse`, `backend/accounts`), DRF token auth + CORS + media settings wired. Spec + code-quality reviewed, approved. Added root `.gitignore`.
- **2026-08-10** — Wrote detailed Phase 1 (Auth) implementation plan: `docs/superpowers/plans/2026-08-10-phase-1-auth.md`. TDD task-by-task, backend (Django+DRF token auth) and frontend (React+Bootstrap). Not yet executed.
- **2026-08-10** — Stack finalized: decoupled Django REST/Channels backend + React+Bootstrap frontend (`backend/` + `frontend/`). Updated `Agent.md`, `docs/plan.md`, `Readme.md`.
- **2026-08-10** — Repo initialized. Wrote `document.md` spec (pre-existing), `docs/plan.md` (5-phase plan), `Agent.md`, `Readme.md`. No code yet.
