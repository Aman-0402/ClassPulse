# Phase 3 — Real-Time Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a student marks attendance, the teacher's dashboard updates instantly (present count, recent-arrivals list, a toast notification) — no page refresh, no polling for attendance events.

**Architecture:** Django Channels, ASGI-served via `daphne` (so `python manage.py runserver` keeps working exactly as documented — Channels' `daphne` app auto-patches `runserver` when listed first in `INSTALLED_APPS`). Channel layer is `InMemoryChannelLayer` — no Redis: this is a single-process dev deployment and adding Redis now would be infrastructure the project doesn't need yet (documented as a prod follow-up). WebSocket auth is a custom middleware (`attendance/ws_auth.py`) reading `?token=` from the query string and resolving it against DRF's existing `Token` model — Channels' built-in `AuthMiddlewareStack` is session-cookie-based and doesn't fit this token-authenticated API. `AttendanceConsumer` joins a per-session group (`attendance_session_<id>`) only after confirming the connecting user is the session's owning teacher. `attendance/services.py::broadcast_attendance_update()` is called from the existing `MarkAttendanceView` after a successful mark — kept in `services.py`, not the view, per Agent.md's "keep WebSocket-triggering logic thin, business logic in services" convention. The QR-rotation mechanism from Phase 2 is untouched — it keeps polling via REST every 15s; only *attendance events* go over the WebSocket.

**Tech Stack:** `channels`, `daphne` (backend); native browser `WebSocket` API (frontend, no client library needed).

---

## File Structure

```text
backend/
├── attendance/
│   ├── ws_auth.py            # NEW — TokenAuthMiddleware for WebSocket auth
│   ├── consumers.py           # NEW — AttendanceConsumer
│   ├── routing.py              # NEW — websocket_urlpatterns
│   ├── services.py              # MODIFY — add broadcast_attendance_update()
│   ├── views.py                  # MODIFY — call broadcast after mark; add SessionLiveView
│   ├── urls.py                    # MODIFY — add session-live route
│   └── tests/
│       ├── test_ws_auth.py          # NEW
│       ├── test_consumer.py          # NEW
│       ├── test_broadcast.py          # NEW
│       └── test_live.py                # NEW
├── classpulse/
│   ├── settings.py            # MODIFY — channels/daphne apps, ASGI_APPLICATION, CHANNEL_LAYERS
│   └── asgi.py                 # MODIFY — ProtocolTypeRouter wiring
└── requirements.txt            # MODIFY — channels, daphne

frontend/src/
├── api/
│   ├── client.ts                # MODIFY — getSessionLive()
│   └── ws.ts                     # NEW — connectToAttendanceSocket()
└── pages/teacher/
    └── LiveQRPage.tsx            # MODIFY — live counter, recent list, toast notifications
```

---

## Task 1: Django Channels scaffold

**Files:**
- Create: `backend/attendance/routing.py`
- Modify: `backend/classpulse/settings.py`
- Modify: `backend/classpulse/asgi.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Install packages**

Run (from `backend/`, venv active):

```
pip install channels daphne
pip freeze > requirements.txt
```

- [ ] **Step 2: Register apps and configure Channels**

In `backend/classpulse/settings.py`, `INSTALLED_APPS` must have `"daphne"` FIRST (before `django.contrib.staticfiles` — Channels' documented requirement so `runserver` auto-switches to ASGI), and `"channels"` added:

```python
INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "channels",
    "accounts",
    "attendance",
]
```

Add near the bottom of the file (after existing settings):

```python
ASGI_APPLICATION = "classpulse.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}
```

- [ ] **Step 3: Create the routing placeholder**

`backend/attendance/routing.py`:

```python
websocket_urlpatterns = []
```

(Task 3 will add the real consumer route here.)

- [ ] **Step 4: Rewrite asgi.py**

`backend/classpulse/asgi.py`:

```python
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "classpulse.settings")
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from attendance.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": URLRouter(websocket_urlpatterns),
    }
)
```

(`get_asgi_application()` must be called BEFORE importing anything that touches Django models — this is Channels' documented ordering requirement, hence the `# noqa: E402` on the below-top imports.)

- [ ] **Step 5: Verify nothing broke**

Run (from `backend/`, venv active):

```
python manage.py check
python manage.py test -v 2
```

Expected: `check` reports no issues; the full test suite still passes at the same count as before this task (35 tests, all from Phases 1-2 — this task adds no new tests, it's pure infra wiring).

- [ ] **Step 6: Commit**

```bash
git add backend/attendance/routing.py backend/classpulse/settings.py backend/classpulse/asgi.py backend/requirements.txt
git commit -m "chore: scaffold Django Channels (in-memory layer, daphne ASGI)"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 2: Token-based WebSocket auth middleware

**Files:**
- Create: `backend/attendance/ws_auth.py`
- Modify: `backend/classpulse/asgi.py`
- Test: `backend/attendance/tests/test_ws_auth.py`

- [ ] **Step 1: Write the failing test**

`backend/attendance/tests/test_ws_auth.py`:

```python
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from rest_framework.authtoken.models import Token
from attendance.ws_auth import TokenAuthMiddleware

User = get_user_model()


class TokenAuthMiddlewareTest(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.token = Token.objects.create(user=self.user)

    async def test_valid_token_sets_user(self):
        captured = {}

        async def dummy_app(scope, receive, send):
            captured["user"] = scope["user"]

        middleware = TokenAuthMiddleware(dummy_app)
        await middleware({"query_string": f"token={self.token.key}".encode(), "type": "websocket"}, None, None)
        self.assertEqual(captured["user"], self.user)

    async def test_missing_token_sets_anonymous(self):
        captured = {}

        async def dummy_app(scope, receive, send):
            captured["user"] = scope["user"]

        middleware = TokenAuthMiddleware(dummy_app)
        await middleware({"query_string": b"", "type": "websocket"}, None, None)
        self.assertTrue(captured["user"].is_anonymous)

    async def test_invalid_token_sets_anonymous(self):
        captured = {}

        async def dummy_app(scope, receive, send):
            captured["user"] = scope["user"]

        middleware = TokenAuthMiddleware(dummy_app)
        await middleware({"query_string": b"token=not-a-real-token", "type": "websocket"}, None, None)
        self.assertTrue(captured["user"].is_anonymous)
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`, venv active): `python manage.py test attendance.tests.test_ws_auth -v 2`
Expected: FAIL — `ModuleNotFoundError: No module named 'attendance.ws_auth'`.

- [ ] **Step 3: Write the middleware**

`backend/attendance/ws_auth.py`:

```python
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token


@database_sync_to_async
def get_user_from_token(token_key):
    try:
        return Token.objects.select_related("user").get(key=token_key).user
    except Token.DoesNotExist:
        return AnonymousUser()


class TokenAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token_key = params.get("token", [None])[0]
        scope["user"] = await get_user_from_token(token_key) if token_key else AnonymousUser()
        return await self.app(scope, receive, send)
```

- [ ] **Step 4: Wire it into asgi.py**

Modify `backend/classpulse/asgi.py` — change the `websocket` line in `ProtocolTypeRouter` from:

```python
        "websocket": URLRouter(websocket_urlpatterns),
```

to:

```python
        "websocket": TokenAuthMiddleware(URLRouter(websocket_urlpatterns)),
```

Add the import: `from attendance.ws_auth import TokenAuthMiddleware  # noqa: E402` (alongside the other below-top imports).

- [ ] **Step 5: Run test to verify it passes**

Run: `python manage.py test attendance.tests.test_ws_auth -v 2`
Expected: `OK` (3 tests pass).

- [ ] **Step 6: Commit**

```bash
git add backend/attendance/ws_auth.py backend/classpulse/asgi.py backend/attendance/tests/test_ws_auth.py
git commit -m "feat: token-based WebSocket auth middleware"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 3: AttendanceConsumer (session-scoped, ownership-checked)

**Files:**
- Create: `backend/attendance/consumers.py`
- Modify: `backend/attendance/routing.py`
- Test: `backend/attendance/tests/test_consumer.py`

- [ ] **Step 1: Write the failing test**

`backend/attendance/tests/test_consumer.py`:

```python
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from rest_framework.authtoken.models import Token
from attendance.models import AttendanceSession
from classpulse.asgi import application

User = get_user_model()


class AttendanceConsumerTest(TransactionTestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.other_teacher = User.objects.create_user(
            username="prof2", password="pw12345678", role=User.ROLE_TEACHER
        )
        self.student = User.objects.create_user(username="stud", password="pw12345678", role=User.ROLE_STUDENT)
        self.teacher_token = Token.objects.create(user=self.teacher)
        self.other_teacher_token = Token.objects.create(user=self.other_teacher)
        self.student_token = Token.objects.create(user=self.student)
        self.session = AttendanceSession.objects.create(teacher=self.teacher, subject="AI")

    async def test_owning_teacher_can_connect(self):
        communicator = WebsocketCommunicator(
            application, f"/ws/attendance/{self.session.id}/?token={self.teacher_token.key}"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_other_teacher_rejected(self):
        communicator = WebsocketCommunicator(
            application, f"/ws/attendance/{self.session.id}/?token={self.other_teacher_token.key}"
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_student_rejected(self):
        communicator = WebsocketCommunicator(
            application, f"/ws/attendance/{self.session.id}/?token={self.student_token.key}"
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_receives_group_broadcast(self):
        from channels.layers import get_channel_layer

        communicator = WebsocketCommunicator(
            application, f"/ws/attendance/{self.session.id}/?token={self.teacher_token.key}"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f"attendance_session_{self.session.id}",
            {"type": "attendance.update", "data": {"name": "Aman Raj", "present_count": 1}},
        )
        message = await communicator.receive_json_from()
        self.assertEqual(message["name"], "Aman Raj")
        self.assertEqual(message["present_count"], 1)
        await communicator.disconnect()
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`, venv active): `python manage.py test attendance.tests.test_consumer -v 2`
Expected: FAIL — `ModuleNotFoundError: No module named 'attendance.consumers'`.

- [ ] **Step 3: Write the consumer**

`backend/attendance/consumers.py`:

```python
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from attendance.models import AttendanceSession


class AttendanceConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.group_name = f"attendance_session_{self.session_id}"
        user = self.scope.get("user")

        if user is None or not user.is_authenticated or user.role != user.ROLE_TEACHER:
            await self.close(code=4403)
            return

        owns_session = await self.session_owned_by(user)
        if not owns_session:
            await self.close(code=4404)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def attendance_update(self, event):
        await self.send_json(event["data"])

    @database_sync_to_async
    def session_owned_by(self, user):
        return AttendanceSession.objects.filter(id=self.session_id, teacher=user).exists()
```

- [ ] **Step 4: Wire the route**

`backend/attendance/routing.py`:

```python
from django.urls import path
from attendance.consumers import AttendanceConsumer

websocket_urlpatterns = [
    path("ws/attendance/<int:session_id>/", AttendanceConsumer.as_asgi()),
]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python manage.py test attendance.tests.test_consumer -v 2`
Expected: `OK` (4 tests pass).

- [ ] **Step 6: Commit**

```bash
git add backend/attendance/consumers.py backend/attendance/routing.py backend/attendance/tests/test_consumer.py
git commit -m "feat: AttendanceConsumer with per-session group and ownership check"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 4: Broadcast attendance updates on successful mark

**Files:**
- Modify: `backend/attendance/services.py`
- Modify: `backend/attendance/views.py`
- Test: `backend/attendance/tests/test_broadcast.py`

- [ ] **Step 1: Write the failing test**

`backend/attendance/tests/test_broadcast.py`:

```python
from unittest.mock import AsyncMock, patch
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from attendance.models import AttendanceSession, QRToken

User = get_user_model()


class BroadcastTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.student = User.objects.create_user(
            username="stud", password="pw12345678", role=User.ROLE_STUDENT, first_name="Aman Raj"
        )
        self.student_token = Token.objects.create(user=self.student)
        self.session = AttendanceSession.objects.create(teacher=self.teacher, subject="AI")
        self.qr = QRToken.objects.create(session=self.session)

    @patch("attendance.services.get_channel_layer")
    def test_mark_attendance_broadcasts_update(self, mock_get_layer):
        mock_layer = AsyncMock()
        mock_get_layer.return_value = mock_layer
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.student_token.key}")

        response = self.client.post(reverse("attendance-mark"), {"token": self.qr.token}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_layer.group_send.assert_called_once()
        group_name, event = mock_layer.group_send.call_args[0]
        self.assertEqual(group_name, f"attendance_session_{self.session.id}")
        self.assertEqual(event["type"], "attendance.update")
        self.assertEqual(event["data"]["name"], "Aman Raj")
        self.assertEqual(event["data"]["present_count"], 1)

    @patch("attendance.services.get_channel_layer")
    def test_broadcast_not_called_on_failed_mark(self, mock_get_layer):
        mock_layer = AsyncMock()
        mock_get_layer.return_value = mock_layer
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.student_token.key}")

        response = self.client.post(reverse("attendance-mark"), {"token": "invalid-token"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_layer.group_send.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`, venv active): `python manage.py test attendance.tests.test_broadcast -v 2`
Expected: FAIL — `AttributeError` or `AssertionError` since `broadcast_attendance_update` doesn't exist yet and nothing calls it.

- [ ] **Step 3: Add the service function**

Add to `backend/attendance/services.py` (append; merge `Attendance` into the existing `from attendance.models import AttendanceSession, QRToken` line, making it `from attendance.models import AttendanceSession, QRToken, Attendance`):

```python
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_attendance_update(attendance):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    profile = getattr(attendance.student, "student_profile", None)
    present_count = Attendance.objects.filter(session=attendance.session).count()
    async_to_sync(channel_layer.group_send)(
        f"attendance_session_{attendance.session_id}",
        {
            "type": "attendance.update",
            "data": {
                "name": attendance.student.get_full_name() or attendance.student.username,
                "crn": profile.crn if profile else "",
                "marked_at": attendance.marked_at.isoformat(),
                "present_count": present_count,
            },
        },
    )
```

- [ ] **Step 4: Call it from the view**

`backend/attendance/views.py`'s `MarkAttendanceView.post()` currently is:

```python
class MarkAttendanceView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def post(self, request):
        serializer = MarkAttendanceSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                attendance = serializer.save()
        except IntegrityError:
            return Response(
                {"detail": "Attendance already marked for this session."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"status": "marked", "marked_at": attendance.marked_at})
```

Change it to call the broadcast after a successful save, before returning:

```python
class MarkAttendanceView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def post(self, request):
        serializer = MarkAttendanceSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                attendance = serializer.save()
        except IntegrityError:
            return Response(
                {"detail": "Attendance already marked for this session."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        broadcast_attendance_update(attendance)
        return Response({"status": "marked", "marked_at": attendance.marked_at})
```

Add `broadcast_attendance_update` to the existing `from attendance.services import get_current_qr_token` import line, making it `from attendance.services import broadcast_attendance_update, get_current_qr_token`.

- [ ] **Step 5: Run test to verify it passes**

Run: `python manage.py test attendance.tests.test_broadcast -v 2`
Expected: `OK` (2 tests pass).

- [ ] **Step 6: Run the full attendance suite**

Run: `python manage.py test attendance -v 2`
Expected: `OK` — all tests pass (no regressions to `test_mark_attendance.py`'s existing 7 tests, which don't mock the channel layer — confirm `get_channel_layer()` against the real in-memory layer configured in Task 1 doesn't error when called without a mock in those pre-existing tests).

- [ ] **Step 7: Commit**

```bash
git add backend/attendance/services.py backend/attendance/views.py backend/attendance/tests/test_broadcast.py
git commit -m "feat: broadcast attendance updates to session WebSocket group on mark"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 5: Live session state endpoint (initial dashboard load)

**Files:**
- Modify: `backend/attendance/views.py`
- Modify: `backend/attendance/urls.py`
- Test: `backend/attendance/tests/test_live.py`

- [ ] **Step 1: Write the failing test**

`backend/attendance/tests/test_live.py`:

```python
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from attendance.models import AttendanceSession, Attendance, QRToken

User = get_user_model()


class SessionLiveTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.student = User.objects.create_user(
            username="stud", password="pw12345678", role=User.ROLE_STUDENT, first_name="Aman Raj"
        )
        self.student_token = Token.objects.create(user=self.student)
        self.teacher_token = Token.objects.create(user=self.teacher)
        self.session = AttendanceSession.objects.create(teacher=self.teacher, subject="AI")

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_requires_teacher_role(self):
        self._auth(self.student_token)
        response = self.client.get(reverse("session-live", args=[self.session.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_present_count_and_recent(self):
        Attendance.objects.create(student=self.student, session=self.session)
        self._auth(self.teacher_token)
        response = self.client.get(reverse("session-live", args=[self.session.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["present_count"], 1)
        self.assertEqual(len(response.data["recent"]), 1)
        self.assertEqual(response.data["recent"][0]["name"], "Aman Raj")

    def test_other_teacher_cannot_view(self):
        other_teacher = User.objects.create_user(
            username="prof2", password="pw12345678", role=User.ROLE_TEACHER
        )
        other_token = Token.objects.create(user=other_teacher)
        self._auth(other_token)
        response = self.client.get(reverse("session-live", args=[self.session.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`, venv active): `python manage.py test attendance.tests.test_live -v 2`
Expected: FAIL — `NoReverseMatch` for `"session-live"`.

- [ ] **Step 3: Add the view**

Add to `backend/attendance/views.py` (append; `Attendance` needs importing — merge into the existing `from attendance.models import AttendanceSession` line, making it `from attendance.models import AttendanceSession, Attendance`):

```python
class SessionLiveView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request, session_id):
        session = get_object_or_404(AttendanceSession, id=session_id, teacher=request.user)
        records = (
            Attendance.objects.filter(session=session)
            .select_related("student", "student__student_profile")
            .order_by("-marked_at")[:10]
        )
        recent = [
            {
                "name": record.student.get_full_name() or record.student.username,
                "crn": getattr(getattr(record.student, "student_profile", None), "crn", ""),
                "marked_at": record.marked_at,
            }
            for record in records
        ]
        present_count = Attendance.objects.filter(session=session).count()
        return Response({"present_count": present_count, "recent": recent})
```

- [ ] **Step 4: Wire URL**

`backend/attendance/urls.py` currently has `from attendance.views import MarkAttendanceView, SessionQRView, StartSessionView, StopSessionView` and four routes. Change the import to `from attendance.views import MarkAttendanceView, SessionLiveView, SessionQRView, StartSessionView, StopSessionView`, and add a new route (keep the existing four):

```python
path("sessions/<int:session_id>/live/", SessionLiveView.as_view(), name="session-live"),
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python manage.py test attendance.tests.test_live -v 2`
Expected: `OK` (3 tests pass).

- [ ] **Step 6: Commit**

```bash
git add backend/attendance/views.py backend/attendance/urls.py backend/attendance/tests/test_live.py
git commit -m "feat: live session state endpoint (present count + recent list)"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 6: Backend sanity check

**Files:** none new — this task verifies everything wired in Tasks 1-5

- [ ] **Step 1: Run the full backend test suite**

Run (from `backend/`, venv active): `python manage.py test -v 2`
Expected: `OK` — all tests pass, no failures, no errors. Report the ACTUAL total count from the output.

- [ ] **Step 2: Confirm the dev server still boots under Channels/daphne**

Run: `python manage.py runserver` briefly (start it, confirm no startup errors/tracebacks in the first few seconds of output, then stop it — this is a manual sanity check, not an automated test). Expected: no import errors, no "Not implemented" ASGI warnings; the console should show Daphne's startup banner (confirming `daphne` in `INSTALLED_APPS` correctly took over `runserver` from the default WSGI dev server) rather than Django's plain "Starting development server at ...".

- [ ] **Step 3: Commit**

Only if Steps 1-2 needed a fix — otherwise there's nothing to commit for this task; it's pure verification. If everything already passes, skip the commit and move to Task 7.

---

## Task 7: Frontend WebSocket client and live-state API call

**Files:**
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/api/ws.ts`

- [ ] **Step 1: Add the live-state REST call**

Add to `frontend/src/api/client.ts` (append at the end of the file, after `markAttendance`; keep all existing exports untouched):

```ts
export interface AttendanceRecord {
  name: string;
  crn: string;
  marked_at: string;
}

export interface LiveSessionResponse {
  present_count: number;
  recent: AttendanceRecord[];
}

export async function getSessionLive(sessionId: number): Promise<LiveSessionResponse> {
  const { data } = await api.get<LiveSessionResponse>(`/attendance/sessions/${sessionId}/live/`);
  return data;
}
```

- [ ] **Step 2: WebSocket client**

`frontend/src/api/ws.ts`:

```ts
const WS_BASE_URL = "ws://localhost:8000/ws";

export interface AttendanceUpdateEvent {
  name: string;
  crn: string;
  marked_at: string;
  present_count: number;
}

export function connectToAttendanceSocket(
  sessionId: number,
  onUpdate: (event: AttendanceUpdateEvent) => void
): WebSocket {
  const token = localStorage.getItem("classpulse_token");
  const socket = new WebSocket(`${WS_BASE_URL}/attendance/${sessionId}/?token=${token ?? ""}`);

  socket.onmessage = (message) => {
    try {
      const data = JSON.parse(message.data) as AttendanceUpdateEvent;
      onUpdate(data);
    } catch {
      // Ignore malformed messages rather than crashing the socket handler.
    }
  };

  return socket;
}
```

- [ ] **Step 3: Verify it compiles**

Run `npm run build` from `frontend/`. Expected: no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/api/ws.ts
git commit -m "feat: frontend WebSocket client and live-session API call"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 8: Live dashboard UI — counter, recent list, toast notifications

**Files:**
- Modify: `frontend/src/pages/teacher/LiveQRPage.tsx`

- [ ] **Step 1: Read the current file**

Read `frontend/src/pages/teacher/LiveQRPage.tsx` first — it currently polls `getSessionQR` every 15s, renders a `QRCodeSVG`, shows an error `Alert` on poll/stop failure (from Phase 2's review fix-passes), and has a "Stop Attendance" button. This task ADDS live-count/list/toast UI alongside the existing QR display — it does not remove any of that.

- [ ] **Step 2: Replace the file with the extended version**

`frontend/src/pages/teacher/LiveQRPage.tsx`:

```tsx
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Container, Button, Spinner, Alert, Badge, ListGroup, Toast, ToastContainer, Row, Col } from "react-bootstrap";
import { QRCodeSVG } from "qrcode.react";
import { getSessionQR, getSessionLive, stopSession, AttendanceRecord } from "../../api/client";
import { connectToAttendanceSocket, AttendanceUpdateEvent } from "../../api/ws";

const QR_REFRESH_MS = 15000;

export default function LiveQRPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [presentCount, setPresentCount] = useState(0);
  const [recent, setRecent] = useState<AttendanceRecord[]>([]);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    const id = Number(sessionId);
    let active = true;
    let debounceTimeout: ReturnType<typeof setTimeout> | undefined;

    const fetchToken = () => {
      getSessionQR(id)
        .then((data) => {
          if (active) {
            setToken(data.token);
            setError(null);
          }
        })
        .catch(() => {
          if (active) setError("Could not refresh the QR code. The session may have ended.");
        });
    };
    fetchToken();
    const interval = setInterval(fetchToken, QR_REFRESH_MS);

    return () => {
      active = false;
      clearInterval(interval);
      if (debounceTimeout) clearTimeout(debounceTimeout);
    };
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) return;
    const id = Number(sessionId);
    let active = true;

    getSessionLive(id).then((data) => {
      if (active) {
        setPresentCount(data.present_count);
        setRecent(data.recent);
      }
    });

    const socket = connectToAttendanceSocket(id, (update: AttendanceUpdateEvent) => {
      if (!active) return;
      setPresentCount(update.present_count);
      setRecent((prev) => [{ name: update.name, crn: update.crn, marked_at: update.marked_at }, ...prev].slice(0, 10));
      setToast(`${update.name} marked present`);
    });

    return () => {
      active = false;
      socket.close();
    };
  }, [sessionId]);

  const handleStop = async () => {
    if (!sessionId) return;
    try {
      await stopSession(Number(sessionId));
    } catch {
      // Already closed or some other failure — either way, nothing more to do here.
    }
    navigate("/teacher/profile");
  };

  return (
    <Container className="py-4">
      <h2 className="text-center">Attendance Live</h2>
      {error && (
        <Alert variant="warning" className="mt-3">
          {error}
        </Alert>
      )}
      <Row className="mt-3">
        <Col md={6} className="text-center">
          {!error && (token ? <QRCodeSVG value={token} size={256} /> : <Spinner animation="border" />)}
          <p className="mt-3 text-muted">QR refreshes every 15 seconds</p>
        </Col>
        <Col md={6}>
          <h4>
            Present: <Badge bg="success">{presentCount}</Badge>
          </h4>
          <ListGroup className="mt-3">
            {recent.map((record, index) => (
              <ListGroup.Item key={`${record.crn}-${index}`}>
                {record.name} <span className="text-muted">({record.crn})</span>
              </ListGroup.Item>
            ))}
          </ListGroup>
        </Col>
      </Row>
      <div className="text-center mt-4">
        <Button variant="danger" onClick={handleStop}>
          Stop Attendance
        </Button>
      </div>
      <ToastContainer position="top-end" className="p-3">
        <Toast show={!!toast} onClose={() => setToast(null)} delay={3000} autohide bg="success">
          <Toast.Body className="text-white">{toast}</Toast.Body>
        </Toast>
      </ToastContainer>
    </Container>
  );
}
```

- [ ] **Step 3: Verify it builds**

Run `npm run build` from `frontend/`. Expected: no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/teacher/LiveQRPage.tsx
git commit -m "feat: live attendance counter, recent list, and toast notifications"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Phase 3 Exit Criteria (from docs/plan.md)

- [ ] With the dashboard open in one browser and a scan happening in another, the dashboard updates within ~1s with no manual refresh (present count, recent list, toast).
- [ ] WebSocket connection is authenticated and scoped — only the owning teacher can connect to a session's group.
- [ ] QR rotation (Phase 2) continues to work unaffected — this phase adds attendance-event push, it doesn't change QR issuance.

## After Completion

Update the Work Log in [`Agent.md`](../../../Agent.md) with a new entry noting Phase 3 is complete, then write Phase 4's detailed plan (`docs/plan.md`'s Security phase: duplicate/expired-QR activity logging, suspicious-activity detection) the same way.
