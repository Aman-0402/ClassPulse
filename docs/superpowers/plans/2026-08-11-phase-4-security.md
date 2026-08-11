# Phase 4 — Security & Suspicious Activity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every attendance attempt — success, duplicate, expired QR, invalid QR, closed session — is logged with who/when/IP/device. A teacher can see these in near-real-time on the dashboard, and a first-pass "new device" heuristic flags when a student's device fingerprint changes between successful marks.

**Architecture:** `MarkAttendanceView`'s validation chain (currently living in `MarkAttendanceSerializer`, Phase 2) moves into `attendance/services.py::mark_attendance()` as a plain function that raises typed exceptions (`attendance/exceptions.py`) — one exception class per failure reason, each carrying an `activity_type`. This lets a single `log_activity()` call happen at each branch point instead of collapsing every failure into one generic 400. A new `ActivityLog` model records every attempt. Non-success activity (duplicate/expired/invalid/closed/new-device) is broadcast over the SAME per-session WebSocket group Phase 3 already built (`AttendanceConsumer`), reusing the group-name convention (`attendance_session_<id>`) and adding a second event type (`activity.update`) alongside the existing `attendance.update`. The teacher dashboard (`LiveQRPage.tsx`) gets a new panel fed by both an initial REST fetch and the live WebSocket stream — mirroring the exact pattern Phase 3 established for the present-count/recent-list panel.

**Tech Stack:** No new backend or frontend dependencies — pure additions to the existing Django/DRF/Channels backend and React/Bootstrap frontend.

---

## File Structure

```text
backend/attendance/
├── exceptions.py           # NEW — AttendanceError and subclasses
├── models.py                 # MODIFY — add ActivityLog
├── services.py                 # MODIFY — mark_attendance(), log_activity(), broadcast_activity_event()
├── serializers.py                # MODIFY — replace MarkAttendanceSerializer with TokenInputSerializer
├── views.py                        # MODIFY — MarkAttendanceView uses mark_attendance(); add SessionActivityView
├── urls.py                           # MODIFY — add session-activity route
├── consumers.py                        # MODIFY — add activity_update handler
├── admin.py                              # MODIFY — register ActivityLog
└── tests/
    ├── test_mark_attendance.py           # MODIFY — rewritten to assert ActivityLog rows per failure type
    ├── test_new_device.py                  # NEW
    ├── test_activity_broadcast.py            # NEW
    └── test_activity_endpoint.py               # NEW

frontend/src/
├── api/
│   ├── client.ts             # MODIFY — getSessionActivity()
│   └── ws.ts                   # MODIFY — route messages by `kind`, add onActivity handler
└── pages/teacher/
    └── LiveQRPage.tsx            # MODIFY — suspicious-activity panel
```

---

## Task 1: ActivityLog model and typed exceptions

**Files:**
- Create: `backend/attendance/exceptions.py`
- Modify: `backend/attendance/models.py`
- Test: `backend/attendance/tests/test_activity_log_model.py`

- [ ] **Step 1: Write the failing test**

`backend/attendance/tests/test_activity_log_model.py`:

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from attendance.models import AttendanceSession, ActivityLog

User = get_user_model()


class ActivityLogModelTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.student = User.objects.create_user(username="stud", password="pw12345678", role=User.ROLE_STUDENT)
        self.session = AttendanceSession.objects.create(teacher=self.teacher, subject="AI")

    def test_can_create_log_with_session(self):
        log = ActivityLog.objects.create(
            student=self.student,
            session=self.session,
            activity_type=ActivityLog.TYPE_DUPLICATE,
            ip_address="127.0.0.1",
            device_info="pytest-agent",
        )
        self.assertEqual(log.activity_type, "duplicate")

    def test_session_is_nullable(self):
        log = ActivityLog.objects.create(
            student=self.student,
            session=None,
            activity_type=ActivityLog.TYPE_INVALID_TOKEN,
        )
        self.assertIsNone(log.session)

    def test_default_ordering_is_newest_first(self):
        first = ActivityLog.objects.create(student=self.student, activity_type=ActivityLog.TYPE_SUCCESS)
        second = ActivityLog.objects.create(student=self.student, activity_type=ActivityLog.TYPE_SUCCESS)
        logs = list(ActivityLog.objects.all())
        self.assertEqual(logs, [second, first])
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`, venv active): `python manage.py test attendance.tests.test_activity_log_model -v 2`
Expected: FAIL — `ImportError: cannot import name 'ActivityLog' from 'attendance.models'`.

- [ ] **Step 3: Add the model**

Append to `backend/attendance/models.py` (keep everything above it — `AttendanceSession`, `QRToken`, `Attendance` — unchanged):

```python
class ActivityLog(models.Model):
    TYPE_SUCCESS = "success"
    TYPE_DUPLICATE = "duplicate"
    TYPE_EXPIRED_TOKEN = "expired_token"
    TYPE_INVALID_TOKEN = "invalid_token"
    TYPE_SESSION_CLOSED = "session_closed"
    TYPE_NEW_DEVICE = "new_device"
    TYPE_CHOICES = [
        (TYPE_SUCCESS, "Success"),
        (TYPE_DUPLICATE, "Duplicate Attempt"),
        (TYPE_EXPIRED_TOKEN, "Expired QR"),
        (TYPE_INVALID_TOKEN, "Invalid QR"),
        (TYPE_SESSION_CLOSED, "Session Closed"),
        (TYPE_NEW_DEVICE, "New Device"),
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activity_logs"
    )
    session = models.ForeignKey(
        AttendanceSession, on_delete=models.CASCADE, related_name="activity_logs", null=True, blank=True
    )
    activity_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.student} ({self.created_at})"
```

`session` is nullable because an invalid-token attempt has no resolvable session — the token doesn't exist, so there's nothing to link to.

- [ ] **Step 4: Add the exceptions module**

`backend/attendance/exceptions.py`:

```python
class AttendanceError(Exception):
    activity_type = "invalid_token"
    message = "Invalid QR code."


class InvalidTokenError(AttendanceError):
    activity_type = "invalid_token"
    message = "Invalid QR code."


class SessionClosedError(AttendanceError):
    activity_type = "session_closed"
    message = "This attendance session is closed."


class ExpiredTokenError(AttendanceError):
    activity_type = "expired_token"
    message = "QR code expired. Please scan the current QR code."


class DuplicateAttendanceError(AttendanceError):
    activity_type = "duplicate"
    message = "Attendance already marked for this session."
```

- [ ] **Step 5: Make and run migrations**

```
python manage.py makemigrations attendance
python manage.py migrate
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python manage.py test attendance.tests.test_activity_log_model -v 2`
Expected: `OK` (3 tests pass).

- [ ] **Step 7: Commit**

```bash
git add backend/attendance/models.py backend/attendance/exceptions.py backend/attendance/migrations backend/attendance/tests/test_activity_log_model.py
git commit -m "feat: add ActivityLog model and typed attendance exceptions"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 2: Refactor mark-attendance into an exception-driven, logged service

**Files:**
- Modify: `backend/attendance/serializers.py`
- Modify: `backend/attendance/services.py`
- Modify: `backend/attendance/views.py`
- Modify: `backend/attendance/tests/test_mark_attendance.py` (full rewrite)

- [ ] **Step 1: Rewrite the test file first (TDD — this defines the new contract)**

Replace the full contents of `backend/attendance/tests/test_mark_attendance.py` with:

```python
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from attendance.models import AttendanceSession, QRToken, Attendance, ActivityLog

User = get_user_model()


class MarkAttendanceTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.student = User.objects.create_user(username="stud", password="pw12345678", role=User.ROLE_STUDENT)
        self.teacher_token = Token.objects.create(user=self.teacher)
        self.student_token = Token.objects.create(user=self.student)
        self.session = AttendanceSession.objects.create(teacher=self.teacher, subject="AI")
        self.qr = QRToken.objects.create(session=self.session)

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_student_can_mark_attendance(self):
        self._auth(self.student_token)
        response = self.client.post(reverse("attendance-mark"), {"token": self.qr.token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Attendance.objects.count(), 1)
        self.assertEqual(ActivityLog.objects.filter(activity_type=ActivityLog.TYPE_SUCCESS).count(), 1)

    def test_teacher_cannot_mark_attendance(self):
        self._auth(self.teacher_token)
        response = self.client.post(reverse("attendance-mark"), {"token": self.qr.token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_token_rejected_and_logged(self):
        self._auth(self.student_token)
        response = self.client.post(reverse("attendance-mark"), {"token": "not-a-real-token"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ActivityLog.objects.filter(activity_type=ActivityLog.TYPE_INVALID_TOKEN).count(), 1)

    def test_expired_token_rejected_and_logged(self):
        self.qr.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        self.qr.save()
        self._auth(self.student_token)
        response = self.client.post(reverse("attendance-mark"), {"token": self.qr.token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ActivityLog.objects.filter(activity_type=ActivityLog.TYPE_EXPIRED_TOKEN).count(), 1)

    def test_duplicate_attendance_rejected_and_logged(self):
        self._auth(self.student_token)
        url = reverse("attendance-mark")
        self.client.post(url, {"token": self.qr.token}, format="json")
        second_qr = QRToken.objects.create(session=self.session)
        response = self.client.post(url, {"token": second_qr.token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Attendance.objects.count(), 1)
        self.assertEqual(ActivityLog.objects.filter(activity_type=ActivityLog.TYPE_DUPLICATE).count(), 1)

    def test_closed_session_rejected_and_logged(self):
        self.session.status = AttendanceSession.STATUS_CLOSED
        self.session.save()
        self._auth(self.student_token)
        response = self.client.post(reverse("attendance-mark"), {"token": self.qr.token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ActivityLog.objects.filter(activity_type=ActivityLog.TYPE_SESSION_CLOSED).count(), 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`, venv active): `python manage.py test attendance.tests.test_mark_attendance -v 2`
Expected: FAIL — the new tests reference `ActivityLog` rows that nothing creates yet (0 != 1 assertion errors), since `MarkAttendanceView` still uses the old `MarkAttendanceSerializer` path.

- [ ] **Step 3: Replace `MarkAttendanceSerializer` with a minimal input serializer**

In `backend/attendance/serializers.py`, DELETE the entire `MarkAttendanceSerializer` class (all validation logic is moving to `services.py`) and replace it with:

```python
class TokenInputSerializer(serializers.Serializer):
    token = serializers.CharField()
```

The file's other classes (`StartSessionSerializer`, `SessionSerializer`, `QRTokenSerializer`) are unchanged. The `Attendance` import at the top (`from attendance.models import AttendanceSession, QRToken, Attendance`) is no longer used by this file after the deletion — change it to `from attendance.models import AttendanceSession, QRToken`.

- [ ] **Step 4: Add `mark_attendance` and `log_activity` to services.py**

`backend/attendance/services.py`'s current full content is:

```python
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from attendance.models import AttendanceSession, QRToken, Attendance

logger = logging.getLogger(__name__)


def get_current_qr_token(session: AttendanceSession) -> QRToken:
    latest = session.qr_tokens.order_by("-created_at", "-id").first()
    if latest and not latest.is_expired():
        return latest
    return QRToken.objects.create(session=session)


def broadcast_attendance_update(attendance):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    profile = getattr(attendance.student, "student_profile", None)
    present_count = Attendance.objects.filter(session=attendance.session).count()
    try:
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
    except Exception:
        logger.exception("Failed to broadcast attendance update for attendance id=%s", attendance.id)
```

Replace it in full with:

```python
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import IntegrityError, transaction

from attendance.exceptions import (
    DuplicateAttendanceError,
    ExpiredTokenError,
    InvalidTokenError,
    SessionClosedError,
)
from attendance.models import ActivityLog, AttendanceSession, QRToken, Attendance

logger = logging.getLogger(__name__)


def get_current_qr_token(session: AttendanceSession) -> QRToken:
    latest = session.qr_tokens.order_by("-created_at", "-id").first()
    if latest and not latest.is_expired():
        return latest
    return QRToken.objects.create(session=session)


def broadcast_attendance_update(attendance):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    profile = getattr(attendance.student, "student_profile", None)
    present_count = Attendance.objects.filter(session=attendance.session).count()
    try:
        async_to_sync(channel_layer.group_send)(
            f"attendance_session_{attendance.session_id}",
            {
                "type": "attendance.update",
                "data": {
                    "kind": "attendance",
                    "name": attendance.student.get_full_name() or attendance.student.username,
                    "crn": profile.crn if profile else "",
                    "marked_at": attendance.marked_at.isoformat(),
                    "present_count": present_count,
                },
            },
        )
    except Exception:
        logger.exception("Failed to broadcast attendance update for attendance id=%s", attendance.id)


def broadcast_activity_event(log_entry):
    if log_entry.session_id is None:
        return
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    try:
        async_to_sync(channel_layer.group_send)(
            f"attendance_session_{log_entry.session_id}",
            {
                "type": "activity.update",
                "data": {
                    "kind": "activity",
                    "activity_type": log_entry.activity_type,
                    "student": log_entry.student.get_full_name() or log_entry.student.username,
                    "created_at": log_entry.created_at.isoformat(),
                },
            },
        )
    except Exception:
        logger.exception("Failed to broadcast activity event id=%s", log_entry.id)


def log_activity(student, session, activity_type, ip_address="", device_info=""):
    entry = ActivityLog.objects.create(
        student=student,
        session=session,
        activity_type=activity_type,
        ip_address=ip_address or None,
        device_info=device_info,
    )
    if activity_type != ActivityLog.TYPE_SUCCESS:
        broadcast_activity_event(entry)
    return entry


def mark_attendance(student, token_value, ip_address, device_info):
    try:
        qr_token = QRToken.objects.select_related("session").get(token=token_value)
    except QRToken.DoesNotExist:
        log_activity(student, None, ActivityLog.TYPE_INVALID_TOKEN, ip_address, device_info)
        raise InvalidTokenError()

    session = qr_token.session

    if session.status != AttendanceSession.STATUS_ACTIVE:
        log_activity(student, session, ActivityLog.TYPE_SESSION_CLOSED, ip_address, device_info)
        raise SessionClosedError()

    if qr_token.is_expired():
        log_activity(student, session, ActivityLog.TYPE_EXPIRED_TOKEN, ip_address, device_info)
        raise ExpiredTokenError()

    if Attendance.objects.filter(student=student, session=session).exists():
        log_activity(student, session, ActivityLog.TYPE_DUPLICATE, ip_address, device_info)
        raise DuplicateAttendanceError()

    try:
        with transaction.atomic():
            attendance = Attendance.objects.create(
                student=student, session=session, ip_address=ip_address or None, device_info=device_info
            )
    except IntegrityError:
        log_activity(student, session, ActivityLog.TYPE_DUPLICATE, ip_address, device_info)
        raise DuplicateAttendanceError()

    log_activity(student, session, ActivityLog.TYPE_SUCCESS, ip_address, device_info)
    broadcast_attendance_update(attendance)
    return attendance
```

Note `broadcast_attendance_update`'s only change is the added `"kind": "attendance"` key inside `data` — this is additive and doesn't break the existing `test_broadcast.py` assertions (they check specific keys, not the full dict).

- [ ] **Step 5: Update the view**

`backend/attendance/views.py`'s current full content is:

```python
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsTeacher, IsStudent
from attendance.models import AttendanceSession, Attendance
from attendance.serializers import MarkAttendanceSerializer, QRTokenSerializer, SessionSerializer, StartSessionSerializer
from attendance.services import broadcast_attendance_update, get_current_qr_token


class StartSessionView(generics.CreateAPIView):
    serializer_class = StartSessionSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeacher]


class StopSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def post(self, request, session_id):
        session = get_object_or_404(AttendanceSession, id=session_id, teacher=request.user)
        if session.status == AttendanceSession.STATUS_CLOSED:
            return Response({"detail": "Session already closed."}, status=400)
        session.status = AttendanceSession.STATUS_CLOSED
        session.end_time = timezone.now()
        session.save(update_fields=["status", "end_time"])
        return Response(SessionSerializer(session).data)


class SessionQRView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request, session_id):
        session = get_object_or_404(AttendanceSession, id=session_id, teacher=request.user)
        token = get_current_qr_token(session)
        return Response(QRTokenSerializer(token).data)


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

Replace it in full with:

```python
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsTeacher, IsStudent
from attendance.exceptions import AttendanceError
from attendance.models import AttendanceSession, Attendance
from attendance.serializers import QRTokenSerializer, SessionSerializer, StartSessionSerializer, TokenInputSerializer
from attendance.services import get_current_qr_token, mark_attendance


class StartSessionView(generics.CreateAPIView):
    serializer_class = StartSessionSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeacher]


class StopSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def post(self, request, session_id):
        session = get_object_or_404(AttendanceSession, id=session_id, teacher=request.user)
        if session.status == AttendanceSession.STATUS_CLOSED:
            return Response({"detail": "Session already closed."}, status=400)
        session.status = AttendanceSession.STATUS_CLOSED
        session.end_time = timezone.now()
        session.save(update_fields=["status", "end_time"])
        return Response(SessionSerializer(session).data)


class SessionQRView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request, session_id):
        session = get_object_or_404(AttendanceSession, id=session_id, teacher=request.user)
        token = get_current_qr_token(session)
        return Response(QRTokenSerializer(token).data)


class MarkAttendanceView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def post(self, request):
        serializer = TokenInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            attendance = mark_attendance(
                student=request.user,
                token_value=serializer.validated_data["token"],
                ip_address=request.META.get("REMOTE_ADDR"),
                device_info=request.META.get("HTTP_USER_AGENT", "")[:255],
            )
        except AttendanceError as exc:
            return Response({"detail": exc.message}, status=400)
        return Response({"status": "marked", "marked_at": attendance.marked_at})


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

(`IntegrityError`/`transaction`/`status` imports are dropped — no longer used in this file; `SessionActivityView` is added in Task 5, not here.)

- [ ] **Step 6: Run test to verify it passes**

Run: `python manage.py test attendance.tests.test_mark_attendance -v 2`
Expected: `OK` (6 tests pass).

- [ ] **Step 7: Run the full attendance suite**

Run: `python manage.py test attendance -v 2`
Expected: `OK` — no regressions in `test_broadcast.py` (checks `event["type"] == "attendance.update"` and specific `data` keys, unaffected by the added `kind` key) or any other pre-existing test file.

- [ ] **Step 8: Commit**

```bash
git add backend/attendance/serializers.py backend/attendance/services.py backend/attendance/views.py backend/attendance/tests/test_mark_attendance.py
git commit -m "refactor: move mark-attendance validation into services.py with per-branch activity logging"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 3: New-device detection on successful mark

**Files:**
- Modify: `backend/attendance/services.py`
- Test: `backend/attendance/tests/test_new_device.py`

- [ ] **Step 1: Write the failing test**

`backend/attendance/tests/test_new_device.py`:

```python
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from attendance.models import AttendanceSession, QRToken, ActivityLog

User = get_user_model()


class NewDeviceDetectionTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.student = User.objects.create_user(username="stud", password="pw12345678", role=User.ROLE_STUDENT)
        self.student_token = Token.objects.create(user=self.student)
        self.session1 = AttendanceSession.objects.create(teacher=self.teacher, subject="AI")
        self.qr1 = QRToken.objects.create(session=self.session1)
        self.session2 = AttendanceSession.objects.create(teacher=self.teacher, subject="AI-2")
        self.qr2 = QRToken.objects.create(session=self.session2)

    def test_new_device_detected_on_change(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.student_token.key}", HTTP_USER_AGENT="DeviceA")
        r1 = self.client.post(reverse("attendance-mark"), {"token": self.qr1.token}, format="json")
        self.assertEqual(r1.status_code, status.HTTP_200_OK)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.student_token.key}", HTTP_USER_AGENT="DeviceB")
        r2 = self.client.post(reverse("attendance-mark"), {"token": self.qr2.token}, format="json")
        self.assertEqual(r2.status_code, status.HTTP_200_OK)

        self.assertEqual(ActivityLog.objects.filter(activity_type=ActivityLog.TYPE_NEW_DEVICE).count(), 1)

    def test_same_device_not_flagged(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.student_token.key}", HTTP_USER_AGENT="DeviceA")
        self.client.post(reverse("attendance-mark"), {"token": self.qr1.token}, format="json")
        self.client.post(reverse("attendance-mark"), {"token": self.qr2.token}, format="json")

        self.assertEqual(ActivityLog.objects.filter(activity_type=ActivityLog.TYPE_NEW_DEVICE).count(), 0)

    def test_first_ever_mark_not_flagged(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.student_token.key}", HTTP_USER_AGENT="DeviceA")
        response = self.client.post(reverse("attendance-mark"), {"token": self.qr1.token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ActivityLog.objects.filter(activity_type=ActivityLog.TYPE_NEW_DEVICE).count(), 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`, venv active): `python manage.py test attendance.tests.test_new_device -v 2`
Expected: FAIL — `test_new_device_detected_on_change` fails because nothing currently creates a `TYPE_NEW_DEVICE` log.

- [ ] **Step 3: Add the detection logic**

In `backend/attendance/services.py`, modify `mark_attendance` — insert the new-device check right before the final `log_activity(student, session, ActivityLog.TYPE_SUCCESS, ...)` call. Change this final section of the function from:

```python
    log_activity(student, session, ActivityLog.TYPE_SUCCESS, ip_address, device_info)
    broadcast_attendance_update(attendance)
    return attendance
```

to:

```python
    previous_device = (
        ActivityLog.objects.filter(student=student, activity_type=ActivityLog.TYPE_SUCCESS)
        .exclude(device_info="")
        .order_by("-created_at")
        .values_list("device_info", flat=True)
        .first()
    )
    if previous_device and device_info and previous_device != device_info:
        log_activity(student, session, ActivityLog.TYPE_NEW_DEVICE, ip_address, device_info)

    log_activity(student, session, ActivityLog.TYPE_SUCCESS, ip_address, device_info)
    broadcast_attendance_update(attendance)
    return attendance
```

This query runs BEFORE today's success is logged, so it naturally only sees PRIOR successful marks — it can't match against the attempt currently in progress.

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test attendance.tests.test_new_device -v 2`
Expected: `OK` (3 tests pass).

- [ ] **Step 5: Run the full attendance suite**

Run: `python manage.py test attendance -v 2`
Expected: `OK` — no regressions.

- [ ] **Step 6: Commit**

```bash
git add backend/attendance/services.py backend/attendance/tests/test_new_device.py
git commit -m "feat: detect and log device change between successful attendance marks"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 4: Broadcast suspicious activity to the session WebSocket group

**Files:**
- Modify: `backend/attendance/consumers.py`
- Test: `backend/attendance/tests/test_activity_broadcast.py`

- [ ] **Step 1: Write the failing test**

`backend/attendance/tests/test_activity_broadcast.py`:

```python
from unittest.mock import AsyncMock, patch
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from attendance.models import AttendanceSession, QRToken

User = get_user_model()


class ActivityBroadcastTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.student = User.objects.create_user(username="stud", password="pw12345678", role=User.ROLE_STUDENT)
        self.student_token = Token.objects.create(user=self.student)
        self.session = AttendanceSession.objects.create(teacher=self.teacher, subject="AI")
        self.qr = QRToken.objects.create(session=self.session)

    def _auth(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.student_token.key}")

    @patch("attendance.services.get_channel_layer")
    def test_expired_token_broadcasts_activity_event(self, mock_get_layer):
        mock_layer = AsyncMock()
        mock_get_layer.return_value = mock_layer
        self.qr.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        self.qr.save()
        self._auth()

        self.client.post(reverse("attendance-mark"), {"token": self.qr.token}, format="json")

        mock_layer.group_send.assert_called_once()
        group_name, event = mock_layer.group_send.call_args[0]
        self.assertEqual(group_name, f"attendance_session_{self.session.id}")
        self.assertEqual(event["type"], "activity.update")
        self.assertEqual(event["data"]["activity_type"], "expired_token")

    @patch("attendance.services.get_channel_layer")
    def test_invalid_token_does_not_broadcast(self, mock_get_layer):
        mock_layer = AsyncMock()
        mock_get_layer.return_value = mock_layer
        self._auth()

        self.client.post(reverse("attendance-mark"), {"token": "not-a-real-token"}, format="json")

        mock_layer.group_send.assert_not_called()

    @patch("attendance.services.get_channel_layer")
    def test_successful_mark_broadcasts_attendance_not_activity(self, mock_get_layer):
        mock_layer = AsyncMock()
        mock_get_layer.return_value = mock_layer
        self._auth()

        self.client.post(reverse("attendance-mark"), {"token": self.qr.token}, format="json")

        mock_layer.group_send.assert_called_once()
        _, event = mock_layer.group_send.call_args[0]
        self.assertEqual(event["type"], "attendance.update")
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`, venv active): `python manage.py test attendance.tests.test_activity_broadcast -v 2`
Expected: PASS for all three already — Task 2's `services.py` already wired `broadcast_activity_event`/`log_activity` correctly. This test file exists to LOCK IN that behavior with a dedicated, focused test suite (the individual pieces were exercised incidentally by Task 2/3's tests, but not asserted this explicitly). If it doesn't pass, something in Task 2/3 was implemented incorrectly — treat that as the bug to fix, not this test.

- [ ] **Step 3: Add the consumer handler**

`backend/attendance/consumers.py` currently has `attendance_update` as its only event handler. Add a sibling handler — append to the class, right after `attendance_update`:

```python
    async def activity_update(self, event):
        await self.send_json(event["data"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test attendance.tests.test_activity_broadcast -v 2`
Expected: `OK` (3 tests pass).

- [ ] **Step 5: Run the full attendance suite**

Run: `python manage.py test attendance -v 2`
Expected: `OK` — no regressions.

- [ ] **Step 6: Commit**

```bash
git add backend/attendance/consumers.py backend/attendance/tests/test_activity_broadcast.py
git commit -m "feat: relay suspicious-activity events over the session WebSocket group"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 5: Teacher activity-log endpoint (initial dashboard load)

**Files:**
- Modify: `backend/attendance/views.py`
- Modify: `backend/attendance/urls.py`
- Test: `backend/attendance/tests/test_activity_endpoint.py`

- [ ] **Step 1: Write the failing test**

`backend/attendance/tests/test_activity_endpoint.py`:

```python
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from attendance.models import AttendanceSession, QRToken

User = get_user_model()


class SessionActivityEndpointTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.student = User.objects.create_user(
            username="stud", password="pw12345678", role=User.ROLE_STUDENT, first_name="Aman Raj"
        )
        self.student_token = Token.objects.create(user=self.student)
        self.teacher_token = Token.objects.create(user=self.teacher)
        self.session = AttendanceSession.objects.create(teacher=self.teacher, subject="AI")
        self.qr = QRToken.objects.create(session=self.session)

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_requires_teacher_role(self):
        self._auth(self.student_token)
        response = self.client.get(reverse("session-activity", args=[self.session.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_teacher_cannot_view(self):
        other_teacher = User.objects.create_user(username="prof2", password="pw12345678", role=User.ROLE_TEACHER)
        other_token = Token.objects.create(user=other_teacher)
        self._auth(other_token)
        response = self.client.get(reverse("session-activity", args=[self.session.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_returns_suspicious_entries_excluding_success(self):
        self._auth(self.student_token)
        self.client.post(reverse("attendance-mark"), {"token": self.qr.token}, format="json")
        second_qr = QRToken.objects.create(session=self.session)
        self.client.post(reverse("attendance-mark"), {"token": second_qr.token}, format="json")

        self._auth(self.teacher_token)
        response = self.client.get(reverse("session-activity", args=[self.session.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["logs"]), 1)
        self.assertEqual(response.data["logs"][0]["activity_type"], "duplicate")
        self.assertEqual(response.data["logs"][0]["student"], "Aman Raj")
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`, venv active): `python manage.py test attendance.tests.test_activity_endpoint -v 2`
Expected: FAIL — `NoReverseMatch` for `"session-activity"`.

- [ ] **Step 3: Add the view**

Add to `backend/attendance/views.py` (append; `ActivityLog` needs importing — merge into the existing `from attendance.models import AttendanceSession, Attendance` line, making it `from attendance.models import AttendanceSession, Attendance, ActivityLog`):

```python
class SessionActivityView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request, session_id):
        session = get_object_or_404(AttendanceSession, id=session_id, teacher=request.user)
        logs = (
            ActivityLog.objects.filter(session=session)
            .exclude(activity_type=ActivityLog.TYPE_SUCCESS)
            .select_related("student")[:50]
        )
        data = [
            {
                "activity_type": log.activity_type,
                "student": log.student.get_full_name() or log.student.username,
                "created_at": log.created_at,
            }
            for log in logs
        ]
        return Response({"logs": data})
```

- [ ] **Step 4: Wire URL**

`backend/attendance/urls.py` currently imports `MarkAttendanceView, SessionLiveView, SessionQRView, StartSessionView, StopSessionView`. Change to also import `SessionActivityView`, and add a route (keep the existing five):

```python
path("sessions/<int:session_id>/activity/", SessionActivityView.as_view(), name="session-activity"),
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python manage.py test attendance.tests.test_activity_endpoint -v 2`
Expected: `OK` (3 tests pass).

- [ ] **Step 6: Commit**

```bash
git add backend/attendance/views.py backend/attendance/urls.py backend/attendance/tests/test_activity_endpoint.py
git commit -m "feat: teacher activity-log endpoint (suspicious entries, ownership-scoped)"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 6: Admin registration and backend sanity check

**Files:**
- Modify: `backend/attendance/admin.py`

- [ ] **Step 1: Register ActivityLog**

`backend/attendance/admin.py` currently registers `AttendanceSession`, `QRToken`, `Attendance`. Add `ActivityLog`:

```python
from django.contrib import admin
from attendance.models import AttendanceSession, QRToken, Attendance, ActivityLog

admin.site.register(AttendanceSession)
admin.site.register(QRToken)
admin.site.register(Attendance)
admin.site.register(ActivityLog)
```

- [ ] **Step 2: Run the full backend test suite**

Run (from `backend/`, venv active): `python manage.py test -v 2`
Expected: `OK` — all tests pass. Report the ACTUAL total count from the output.

- [ ] **Step 3: Commit**

```bash
git add backend/attendance/admin.py
git commit -m "feat: register ActivityLog in admin"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 7: Frontend — suspicious-activity panel

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/ws.ts`
- Modify: `frontend/src/pages/teacher/LiveQRPage.tsx`

- [ ] **Step 1: Add the activity-log REST call**

Add to `frontend/src/api/client.ts` (append at the end, after `getSessionLive`; keep all existing exports untouched):

```ts
export interface ActivityLogEntry {
  activity_type: "duplicate" | "expired_token" | "invalid_token" | "session_closed" | "new_device";
  student: string;
  created_at: string;
}

export interface ActivityLogResponse {
  logs: ActivityLogEntry[];
}

export async function getSessionActivity(sessionId: number): Promise<ActivityLogResponse> {
  const { data } = await api.get<ActivityLogResponse>(`/attendance/sessions/${sessionId}/activity/`);
  return data;
}
```

- [ ] **Step 2: Extend the WebSocket client to route by message kind**

`frontend/src/api/ws.ts` currently is:

```ts
const WS_BASE_URL = "ws://localhost:8000/ws";
const RECONNECT_DELAY_MS = 3000;

export interface AttendanceUpdateEvent {
  name: string;
  crn: string;
  marked_at: string;
  present_count: number;
}

export interface AttendanceSocketHandlers {
  onUpdate: (event: AttendanceUpdateEvent) => void;
  onStatusChange?: (status: "connected" | "disconnected" | "reconnecting") => void;
}

export interface AttendanceSocketHandle {
  close: () => void;
}

export function connectToAttendanceSocket(
  sessionId: number,
  handlers: AttendanceSocketHandlers
): AttendanceSocketHandle {
  let closedByCaller = false;
  let socket: WebSocket | null = null;
  let reconnectTimeout: ReturnType<typeof setTimeout> | undefined;

  const open = () => {
    const token = localStorage.getItem("classpulse_token");
    socket = new WebSocket(`${WS_BASE_URL}/attendance/${sessionId}/?token=${token ?? ""}`);

    socket.onopen = () => {
      handlers.onStatusChange?.("connected");
    };

    socket.onmessage = (message) => {
      try {
        const data = JSON.parse(message.data) as AttendanceUpdateEvent;
        handlers.onUpdate(data);
      } catch {
        // Ignore malformed messages rather than crashing the socket handler.
      }
    };

    socket.onerror = () => {
      handlers.onStatusChange?.("disconnected");
    };

    socket.onclose = () => {
      if (closedByCaller) return;
      handlers.onStatusChange?.("reconnecting");
      reconnectTimeout = setTimeout(open, RECONNECT_DELAY_MS);
    };
  };

  open();

  return {
    close: () => {
      closedByCaller = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      socket?.close();
    },
  };
}
```

Replace it in full with:

```ts
const WS_BASE_URL = "ws://localhost:8000/ws";
const RECONNECT_DELAY_MS = 3000;

export interface AttendanceUpdateEvent {
  kind: "attendance";
  name: string;
  crn: string;
  marked_at: string;
  present_count: number;
}

export interface ActivityUpdateEvent {
  kind: "activity";
  activity_type: "duplicate" | "expired_token" | "invalid_token" | "session_closed" | "new_device";
  student: string;
  created_at: string;
}

export interface AttendanceSocketHandlers {
  onUpdate: (event: AttendanceUpdateEvent) => void;
  onActivity?: (event: ActivityUpdateEvent) => void;
  onStatusChange?: (status: "connected" | "disconnected" | "reconnecting") => void;
}

export interface AttendanceSocketHandle {
  close: () => void;
}

export function connectToAttendanceSocket(
  sessionId: number,
  handlers: AttendanceSocketHandlers
): AttendanceSocketHandle {
  let closedByCaller = false;
  let socket: WebSocket | null = null;
  let reconnectTimeout: ReturnType<typeof setTimeout> | undefined;

  const open = () => {
    const token = localStorage.getItem("classpulse_token");
    socket = new WebSocket(`${WS_BASE_URL}/attendance/${sessionId}/?token=${token ?? ""}`);

    socket.onopen = () => {
      handlers.onStatusChange?.("connected");
    };

    socket.onmessage = (message) => {
      try {
        const data = JSON.parse(message.data) as AttendanceUpdateEvent | ActivityUpdateEvent;
        if (data.kind === "activity") {
          handlers.onActivity?.(data);
        } else {
          handlers.onUpdate(data);
        }
      } catch {
        // Ignore malformed messages rather than crashing the socket handler.
      }
    };

    socket.onerror = () => {
      handlers.onStatusChange?.("disconnected");
    };

    socket.onclose = () => {
      if (closedByCaller) return;
      handlers.onStatusChange?.("reconnecting");
      reconnectTimeout = setTimeout(open, RECONNECT_DELAY_MS);
    };
  };

  open();

  return {
    close: () => {
      closedByCaller = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      socket?.close();
    },
  };
}
```

- [ ] **Step 3: Add the panel to LiveQRPage.tsx**

Read the current `frontend/src/pages/teacher/LiveQRPage.tsx` first (it has the QR-polling effect, the live-state+WebSocket effect with `presentCount`/`recent`/`toast`/`toastKey`/`wsStatus` state, and the render with QR/badge/list/toast). Apply these additions — DO NOT alter the QR-polling effect or the existing attendance-update handling:

1. Add imports: `getSessionActivity` and `ActivityLogEntry` from `../../api/client` (add to the existing import line and a new `import type` line, matching this file's existing style of separating value imports from `import type`); `ActivityUpdateEvent` as a type import from `../../api/ws`.

2. Add state: `const [activityLog, setActivityLog] = useState<ActivityLogEntry[]>([]);`

3. In the live-state `useEffect` (the one with `getSessionLive` and `connectToAttendanceSocket`), add an initial fetch alongside the existing `getSessionLive` call:

```ts
    getSessionActivity(id)
      .then((data) => {
        if (active) setActivityLog(data.logs);
      })
      .catch(() => {
        // Non-critical panel — a failed initial fetch just leaves it empty; the live WS feed will still populate it going forward.
      });
```

4. Add an `onActivity` handler to the `connectToAttendanceSocket` call, alongside the existing `onUpdate`/`onStatusChange`:

```ts
      onActivity: (event: ActivityUpdateEvent) => {
        if (!active) return;
        setActivityLog((prev) =>
          [{ activity_type: event.activity_type, student: event.student, created_at: event.created_at }, ...prev].slice(0, 20)
        );
      },
```

5. Add a small badge-label helper function above the component (or inline) for turning an `activity_type` into a human label and Bootstrap variant:

```ts
const ACTIVITY_LABELS: Record<ActivityLogEntry["activity_type"], { label: string; variant: string }> = {
  duplicate: { label: "Duplicate scan", variant: "warning" },
  expired_token: { label: "Expired QR", variant: "danger" },
  invalid_token: { label: "Invalid QR", variant: "danger" },
  session_closed: { label: "Closed-session attempt", variant: "secondary" },
  new_device: { label: "New device", variant: "info" },
};
```

6. Render a "Suspicious Activity" panel below the existing `Row` (present-count/recent-list), above the "Stop Attendance" button:

```tsx
      {activityLog.length > 0 && (
        <div className="mt-4">
          <h5>Suspicious Activity</h5>
          <ListGroup>
            {activityLog.map((entry, index) => {
              const meta = ACTIVITY_LABELS[entry.activity_type];
              return (
                <ListGroup.Item key={`${entry.student}-${entry.created_at}-${index}`}>
                  <Badge bg={meta.variant} className="me-2">
                    {meta.label}
                  </Badge>
                  {entry.student}
                </ListGroup.Item>
              );
            })}
          </ListGroup>
        </div>
      )}
```

(This list's `key` includes `index` deliberately, unlike the recent-attendance list's `key={record.crn}` — here, the SAME student can appear multiple times with the SAME `activity_type` in rapid succession, e.g. retrying an expired QR several times, so `student`+`created_at` isn't guaranteed unique on its own if two entries land in the same second; keep the `index` fallback for this list specifically.)

- [ ] **Step 4: Verify it builds**

Run `npm run build` from `frontend/`. Expected: no TypeScript errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/api/ws.ts frontend/src/pages/teacher/LiveQRPage.tsx
git commit -m "feat: suspicious-activity panel on teacher dashboard"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Phase 4 Exit Criteria (from docs/plan.md)

- [ ] Every attendance attempt (success, duplicate, expired-token, invalid-token, closed-session) creates an `ActivityLog` row with student/session/IP/device.
- [ ] A duplicate-scan attempt and an expired-QR attempt both appear in the teacher's activity log in near-real-time, each attributable to a student and device (doc.md §17 examples 1-2).
- [ ] A device change between two successful marks is flagged (`TYPE_NEW_DEVICE`) — first-pass heuristic for doc.md §17 example 3, not a hard block.
- [ ] Duplicate/expired detection is still enforced at the DB/token level exactly as Phase 2 built it — this phase adds observability, it doesn't change what's allowed.

## After Completion

Update the Work Log in [`Agent.md`](../../../Agent.md) with a new entry noting Phase 4 is complete, then write Phase 5's detailed plan (`docs/plan.md`'s Reports phase: attendance history, percentage calculation, Excel/PDF export, analytics) the same way.
