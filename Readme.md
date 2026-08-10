# ClassPulse

Smart QR-Based Real-Time Attendance System — a web app where students mark attendance by scanning a QR code that rotates every 15 seconds, with live monitoring on the teacher's dashboard.

Full functional spec: [`document.md`](document.md). Build plan: [`docs/plan.md`](docs/plan.md). Agent/contributor conventions: [`Agent.md`](Agent.md).

## Why

Manual roll-call is slow and error-prone; static QR codes get photographed and shared. ClassPulse rotates the QR every 15 seconds so a screenshot goes stale almost immediately, and every scan is validated server-side before it counts.

## Features (v1)

- Student self-registration (unique CRN) and login
- Teacher login and session control (start/stop attendance)
- QR code that auto-rotates every 15 seconds
- Server-side scan validation (session active, token valid, not expired, not duplicate)
- Real-time teacher dashboard (live count, live student list, WebSocket-pushed)
- Suspicious-activity detection (duplicate scans, expired-QR attempts, new-device logins)
- Attendance history and percentage, per student
- Teacher analytics (overall + per-student) and XLSX/CSV/PDF export

Out of scope for v1: multiple subjects/teachers, timetabling, geofencing, face verification — see `document.md` §33 for the future roadmap.

## Tech Stack

Python · Django · Django REST Framework · Django Channels (WebSocket) · PostgreSQL (SQLite in dev) · Bootstrap 5

## Getting Started

```bash
python -m venv venv
venv\Scripts\activate        # Windows PowerShell
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Configure `DATABASE_URL` and `SECRET_KEY` via environment variables / `.env` — never commit these.

## Project Status

In planning. See [`docs/plan.md`](docs/plan.md) for the 5-phase build order (Auth → Attendance/QR → Real-Time → Security → Reports).

## Roles

- **Teacher:** start/stop sessions, view live attendance, review suspicious activity, export reports.
- **Student:** register, log in, scan QR, view own attendance history and percentage.
