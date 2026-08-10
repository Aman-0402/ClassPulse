# ClassPulse — Development Plan

Source spec: [`document.md`](../document.md). Stack: decoupled — Django + DRF + Channels backend (`backend/`, PostgreSQL/SQLite), React + Bootstrap 5 frontend (`frontend/`) talking to it over REST + WebSocket.

Each phase ends with a working, demoable slice. No phase depends on future phases' code — only on prior ones.

---

## Phase 1 — Authentication & Profiles

**Goal:** students and teacher can register/login; student has a profile.

**Models:** `Student`, `Teacher` (custom user or `OneToOneField` to Django `User`).

**Backend:**
- Student registration (unique CRN enforced at DB level, unique constraint).
- Student login, Teacher login (Django auth, hashed passwords via Django's PBKDF2 default).
- `GET /api/student/profile`, `GET /api/teacher/profile`.

**Frontend:**
- React registration form component (name, CRN, course, semester, section, email, password, photo upload) calling `POST /api/student/register`.
- Login pages (student, teacher) using React Router (or similar) for routing.
- Student profile page (read-only), Bootstrap-styled.

**Exit criteria:** a student can register, log in, see their profile. A teacher can log in. Duplicate CRN registration rejected with a clear error.

---

## Phase 2 — Attendance Sessions & QR

**Goal:** teacher starts a session; QR rotates every 15s; student scans and gets marked present.

**Models:** `AttendanceSession`, `QRToken`, `Attendance`.

**Backend:**
- `POST /api/sessions/start` (teacher only) — creates `AttendanceSession` (subject, date, start/end time, status=active).
- `POST /api/sessions/{id}/stop`.
- QR token generator: cryptographically random token per `QRToken` row, `expires_at = now + 15s`, tied to `session_id`. Background task (Celery beat, APScheduler, or simple client-poll-triggered generation) issues a new token every 15s while session is active.
- `POST /api/attendance/mark` — student submits scanned token; server runs the validation chain from doc.md §10 (session active → token valid → not expired → student authenticated → not already marked → mark present).
- Enforce one-attendance-per-student-per-session via a DB unique constraint on `(student_id, session_id)`, not just app logic.

**Frontend:**
- Teacher: "Start Attendance" screen showing live QR image (regenerated every 15s via polling or WebSocket-pushed token).
- Student: QR scanner view (camera-based JS QR library) → auto-submits token to `/api/attendance/mark` → shows success/expired/duplicate message.

**Exit criteria:** teacher starts a session, QR visibly changes every 15s, a student scan within the 15s window marks attendance once; a stale QR is rejected; a second scan is rejected as duplicate.

---

## Phase 3 — Real-Time Dashboard

**Goal:** teacher dashboard updates live with no page refresh.

**Backend:**
- Django Channels consumer (`AttendanceConsumer`) on a per-session WebSocket group.
- On successful `mark`, broadcast `{student_name, crn, time}` to the session's group.

**Frontend:**
- Teacher dashboard: live counter (`present/total`), live "recently present" list, WebSocket client subscribing to the session channel.
- Popup/toast notification per attendance event (doc.md §16).

**Exit criteria:** with dashboard open in one browser and a scan happening in another, the dashboard updates within ~1s with no manual refresh.

---

## Phase 4 — Security & Suspicious Activity

**Goal:** log and surface abuse signals; harden validation.

**Models:** `ActivityLog`.

**Backend:**
- Log every attendance attempt (success, duplicate, expired-token, invalid-token) to `ActivityLog` with `ip_address`, `device_info` (User-Agent), `activity_type`.
- Duplicate-device/session heuristic: flag when the same student account is used from a new device/IP within a short window mid-session.
- `GET /api/teacher/activity-log?session_id=` for teacher review.

**Frontend:**
- Teacher: suspicious-activity panel (duplicate scans, expired-QR attempts, new-device logins) surfaced via the same WebSocket group or a polled endpoint.

**Exit criteria:** an expired-QR attempt and a duplicate-scan attempt both appear in the teacher's activity log in near-real-time, each attributable to a student and device.

---

## Phase 5 — Reports & Analytics

**Goal:** history, percentages, exports.

**Backend:**
- Attendance percentage calculation per student per subject (doc.md §21 formula).
- `GET /api/student/attendance-history`, `GET /api/teacher/analytics` (overall + per-student).
- Export endpoints: XLSX (`openpyxl`), CSV (`csv` stdlib), PDF (`reportlab` or `weasyprint`).

**Frontend:**
- Student: attendance history table + percentage.
- Teacher: analytics view (overall rate, per-student breakdown, students-below-threshold list) + export buttons.

**Exit criteria:** teacher downloads an XLSX/CSV/PDF attendance report matching the on-screen data; student sees correct running percentage.

---

## Cross-Phase Notes

- **Security invariant (all phases):** the QR code itself is never trusted client-side — every validation decision happens server-side, per doc.md §18/§34.
- **DB-level constraints**, not just app-level checks, for: unique CRN, one-attendance-per-student-per-session.
- **Out of scope for v1** (doc.md §4): multiple subjects/teachers, timetable management, geofencing, face verification — tracked as Phase 6+ (doc.md §33) if requested later.
