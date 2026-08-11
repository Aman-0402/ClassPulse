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

- **2026-08-11** — Phase 4 Task 3 done: new-device detection — logs `TYPE_NEW_DEVICE` (non-blocking) when a student's User-Agent changes between successful marks. Spec + code-quality reviewed, approved. Flagged for later (not fixed, both non-blocking): exact-string UA comparison will likely false-positive often in real use (browser auto-updates, extensions) — fine for a v1 "log it" heuristic, but shouldn't drive any real alert/notification without normalization first; no DB index on `(student, activity_type, created_at)` for this now-per-mark query, negligible at current scale.
- **2026-08-11** — Phase 4 Task 2 done: mark-attendance validation moved from Phase 2's DRF serializer into `services.py::mark_attendance()`, exception-driven (5 typed exceptions from Task 1), every branch logs an `ActivityLog` row before failing/succeeding. Spec + code-quality reviewed, approved. Fixed one real gap before merge: `log_activity()`'s DB write was unguarded — a transient failure there could turn an already-successful, already-committed attendance mark into a 500 for the student (same failure class as the Phase 3 broadcast fix); wrapped in try/except, logs and continues. Noted, not fixed: double duplicate-check (pre-check + IntegrityError backstop) is intentional TOCTOU-safe redundancy but undocumented; exception classes couple internal `activity_type` with user-facing `message` on one attribute set.
- **2026-08-11** — Phase 4 (Security & Suspicious Activity) started. Wrote detailed plan: `docs/superpowers/plans/2026-08-11-phase-4-security.md` (7 tasks). Task 1 done: `ActivityLog` model (audits every attendance attempt) + `attendance/exceptions.py` (5 typed failure classes, wired up in Task 2). Spec + code-quality reviewed, approved; fixed one real gap before it went live: `session` FK was `CASCADE` (deleting a session would wipe its own audit trail) — changed to `SET_NULL` so log entries survive. Also noted for later, not fixed: `AttendanceError` base class doubles as a usable concrete exception (should be raised only via subclasses; harmless today since nothing raises the base directly).
- **2026-08-11** — Phase 3 Task 8 done (final task): `LiveQRPage` extended with present-count badge, recent list, toast notifications, live-driven by `connectToAttendanceSocket`. Code-quality review found the exact "silent stall, no feedback" pattern this file was already fixed for twice in Phase 2 — reintroduced via unhandled `getSessionLive` rejection and a WebSocket with no error/close handling or reconnect; fixed with `.catch()`, `onerror`/`onclose`/auto-reconnect in `ws.ts`, a status badge, and a stable per-event toast key (also found + fixed: unstable list `key`, and a toast-autohide-timer race where same-named students could dismiss each other's toast early). Re-review caught the toast key fix was incomplete (message-text key still collided for same-named students); tightened to a monotonic counter. Re-verified directly, approved. **Phase 3 (Real-Time Dashboard) complete** — all 8 tasks done, exit criteria met (WebSocket push updates dashboard with no refresh, auth+ownership scoped per session, QR rotation unaffected). Known accepted tradeoff: WebSocket reconnects forever with no backoff/cap if the endpoint is fundamentally broken — flagged as non-blocking follow-up for Phase 4+.
- **2026-08-11** — Phase 3 Task 7 done: frontend `getSessionLive` REST call + `connectToAttendanceSocket` native WebSocket client (token via query string, matches localStorage token). Verified directly (exact-match spec, pure additions).
- **2026-08-11** — Phase 3 Task 6 done: backend sanity check — 49/49 tests passing, `manage.py check` clean, dev server confirmed serving via daphne (`Server: daphne` header, not plain WSGI dev server). Backend half of Phase 3 complete (Tasks 1-6) — moving to frontend (Tasks 7-8).
- **2026-08-11** — Phase 3 Task 5 done: `GET /api/attendance/sessions/<id>/live/` (teacher-only, ownership-scoped) — present count + last-10 recent list, for initial dashboard load before WS events arrive. Spec + code-quality reviewed, approved. Noted for frontend Task 8: WS event payload and REST `recent` items share `{name, crn, marked_at}` shape but `present_count` nests differently (per-event in WS vs. top-level in REST) — plan's Task 8 code already handles this correctly by destructuring explicitly, not reusing types wholesale.
- **2026-08-11** — Phase 3 Task 4 done: `broadcast_attendance_update` called from `MarkAttendanceView` after successful mark, pushes `{name, crn, marked_at, present_count}` to session's WS group. Code-quality review found reliability gap: unguarded `group_send` could turn a successful, already-committed DB write into a 500 for the student; fixed with try/except + logging (never masks a successful mark), also tidied mid-file imports. Re-verified directly, approved.
- **2026-08-11** — Phase 3 Task 3 done: `AttendanceConsumer` — teacher-only, ownership-checked (close 4403/4404), joins `attendance_session_<id>` group. Code-quality review found fragile `disconnect()` guard (`hasattr(self, "group_name")` doesn't actually track join state, since `group_name` is set before auth checks run); fixed with explicit `joined_group` flag. Re-verified directly, approved.
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
