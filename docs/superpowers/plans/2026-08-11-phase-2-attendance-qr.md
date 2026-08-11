# Phase 2 — Attendance Sessions & QR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A teacher can start an attendance session and see a QR code that rotates every 15 seconds; a student can scan it with their camera and get marked present exactly once per session, with every validation decision made server-side.

**Architecture:** New Django app `attendance` (separate from `accounts`, per Agent.md's "one app per bounded concern") holds `AttendanceSession`, `QRToken`, `Attendance`. QR rotation is **lazy**, not a background scheduler: a `GET .../qr/` call returns the current unexpired token, or mints a fresh one if the last one expired — this avoids adding Celery/APScheduler for something a 15-second frontend poll already drives, and keeps the whole flow synchronous and easy to test. A new `accounts/permissions.py` adds `IsTeacher`/`IsStudent` DRF permission classes — these didn't exist after Phase 1 (flagged as a gap in Agent.md's Task 9 log) and Phase 2 is where they become load-bearing: session start/stop/QR are teacher-only, marking attendance is student-only. Business logic (token rotation) lives in `attendance/services.py`, kept thin per Agent.md's convention so it's reusable from Phase 3's WebSocket consumer later. Duplicate attendance is prevented by a DB-level `UniqueConstraint` on `(student, session)`, not just serializer validation — matching the pattern already used for CRN uniqueness in Phase 1.

**Tech Stack:** Django, DRF (existing `TokenAuthentication`), Python `secrets` module for token generation (no new backend dependency); frontend adds `qrcode.react` (renders a QR image from a string, client-side) and `html5-qrcode` (camera-based scanning).

---

## File Structure

```text
backend/
├── accounts/
│   ├── permissions.py          # NEW — IsTeacher, IsStudent
│   └── tests/test_permissions.py  # NEW
├── attendance/                  # NEW Django app
│   ├── models.py                 # AttendanceSession, QRToken, Attendance
│   ├── serializers.py             # StartSessionSerializer, SessionSerializer, QRTokenSerializer, MarkAttendanceSerializer
│   ├── services.py                 # get_current_qr_token()
│   ├── views.py                     # StartSessionView, StopSessionView, SessionQRView, MarkAttendanceView
│   ├── urls.py
│   ├── admin.py
│   └── tests/
│       ├── test_models.py
│       ├── test_sessions.py
│       ├── test_qr.py
│       └── test_mark_attendance.py
└── classpulse/
    ├── settings.py               # MODIFY — register "attendance" app
    └── urls.py                    # MODIFY — include attendance.urls

frontend/src/
├── api/client.ts                 # MODIFY — startSession, stopSession, getSessionQR, markAttendance
├── pages/
│   ├── teacher/
│   │   ├── StartAttendancePage.tsx  # NEW
│   │   └── LiveQRPage.tsx             # NEW
│   ├── student/
│   │   └── ScanQRPage.tsx               # NEW
│   ├── TeacherProfilePage.tsx    # MODIFY — add "Start Attendance" link
│   └── StudentProfilePage.tsx    # MODIFY — add "Scan Attendance QR" link
└── App.tsx                       # MODIFY — new routes
```

---

## Task 1: Role-based permission classes

**Files:**
- Create: `backend/accounts/permissions.py`
- Test: `backend/accounts/tests/test_permissions.py`

- [ ] **Step 1: Write the failing test**

`backend/accounts/tests/test_permissions.py`:

```python
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory
from accounts.permissions import IsTeacher, IsStudent

User = get_user_model()


class RolePermissionTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.student = User.objects.create_user(username="stud", password="pw12345678", role=User.ROLE_STUDENT)

    def _request_for(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_is_teacher_allows_teacher(self):
        self.assertTrue(IsTeacher().has_permission(self._request_for(self.teacher), None))

    def test_is_teacher_rejects_student(self):
        self.assertFalse(IsTeacher().has_permission(self._request_for(self.student), None))

    def test_is_student_allows_student(self):
        self.assertTrue(IsStudent().has_permission(self._request_for(self.student), None))

    def test_is_student_rejects_teacher(self):
        self.assertFalse(IsStudent().has_permission(self._request_for(self.teacher), None))
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`, venv active): `python manage.py test accounts.tests.test_permissions -v 2`
Expected: FAIL — `ModuleNotFoundError: No module named 'accounts.permissions'`.

- [ ] **Step 3: Write the permission classes**

`backend/accounts/permissions.py`:

```python
from rest_framework.permissions import BasePermission
from accounts.models import User


class IsTeacher(BasePermission):
    message = "Only teachers can perform this action."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.ROLE_TEACHER)


class IsStudent(BasePermission):
    message = "Only students can perform this action."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.ROLE_STUDENT)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test accounts.tests.test_permissions -v 2`
Expected: `OK` (4 tests pass).

- [ ] **Step 5: Commit**

```bash
git add backend/accounts/permissions.py backend/accounts/tests/test_permissions.py
git commit -m "feat: add IsTeacher/IsStudent role-based permission classes"
```

**Do NOT add a "Co-Authored-By" trailer.** Repo-wide rule: no co-author trailers on any commit.

---

## Task 2: Attendance app scaffold and models

**Files:**
- Create: `backend/attendance/models.py`, `backend/attendance/__init__.py`, `backend/attendance/apps.py`, `backend/attendance/migrations/__init__.py`
- Modify: `backend/classpulse/settings.py`
- Test: `backend/attendance/tests/test_models.py`, `backend/attendance/tests/__init__.py`

- [ ] **Step 1: Create the app**

Run (from `backend/`, venv active): `python manage.py startapp attendance`

- [ ] **Step 2: Register the app**

In `backend/classpulse/settings.py`, add `"attendance"` to `INSTALLED_APPS`, after `"accounts"`:

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "accounts",
    "attendance",
]
```

- [ ] **Step 3: Write the failing test**

Delete the stock `backend/attendance/tests.py` stub. Create `backend/attendance/tests/__init__.py` (empty) and `backend/attendance/tests/test_models.py`:

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from attendance.models import AttendanceSession, QRToken, Attendance

User = get_user_model()


class AttendanceModelsTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.student = User.objects.create_user(username="stud", password="pw12345678", role=User.ROLE_STUDENT)
        self.session = AttendanceSession.objects.create(teacher=self.teacher, subject="AI")

    def test_session_defaults_to_active(self):
        self.assertEqual(self.session.status, AttendanceSession.STATUS_ACTIVE)

    def test_qr_token_gets_expiry_on_save(self):
        token = QRToken.objects.create(session=self.session)
        self.assertIsNotNone(token.expires_at)
        self.assertFalse(token.is_expired())

    def test_qr_token_is_expired_after_lifetime(self):
        token = QRToken.objects.create(session=self.session)
        token.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        token.save()
        self.assertTrue(token.is_expired())

    def test_duplicate_attendance_rejected_at_db_level(self):
        Attendance.objects.create(student=self.student, session=self.session)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Attendance.objects.create(student=self.student, session=self.session)
```

- [ ] **Step 4: Run test to verify it fails**

Run: `python manage.py test attendance.tests.test_models -v 2`
Expected: FAIL — `ImportError: cannot import name 'AttendanceSession' from 'attendance.models'`.

- [ ] **Step 5: Write the models**

`backend/attendance/models.py`:

```python
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

QR_TOKEN_LIFETIME_SECONDS = 15


def generate_qr_token():
    return secrets.token_urlsafe(24)


class AttendanceSession(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_CLOSED, "Closed"),
    ]

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attendance_sessions"
    )
    subject = models.CharField(max_length=100)
    date = models.DateField(default=timezone.localdate)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} ({self.date})"


class QRToken(models.Model):
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name="qr_tokens")
    token = models.CharField(max_length=64, unique=True, default=generate_qr_token)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(seconds=QR_TOKEN_LIFETIME_SECONDS)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return self.token


class Attendance(models.Model):
    STATUS_PRESENT = "present"
    STATUS_CHOICES = [(STATUS_PRESENT, "Present")]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attendance_records"
    )
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name="attendance_records")
    marked_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PRESENT)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "session"], name="unique_attendance_per_session"),
        ]

    def __str__(self):
        return f"{self.student} - {self.session} ({self.status})"
```

- [ ] **Step 6: Make and run migrations**

```
python manage.py makemigrations attendance
python manage.py migrate
```

- [ ] **Step 7: Run test to verify it passes**

Run: `python manage.py test attendance.tests.test_models -v 2`
Expected: `OK` (4 tests pass).

- [ ] **Step 8: Commit**

```bash
git add backend/attendance backend/classpulse/settings.py
git commit -m "feat: add attendance app with Session/QRToken/Attendance models"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 3: Start & stop session endpoints

**Files:**
- Create: `backend/attendance/serializers.py`
- Create: `backend/attendance/views.py`
- Create: `backend/attendance/urls.py`
- Test: `backend/attendance/tests/test_sessions.py`

- [ ] **Step 1: Write the failing test**

`backend/attendance/tests/test_sessions.py`:

```python
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from attendance.models import AttendanceSession

User = get_user_model()


class SessionLifecycleTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.student = User.objects.create_user(username="stud", password="pw12345678", role=User.ROLE_STUDENT)
        self.teacher_token = Token.objects.create(user=self.teacher)
        self.student_token = Token.objects.create(user=self.student)

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_teacher_can_start_session(self):
        self._auth(self.teacher_token)
        response = self.client.post(reverse("session-start"), {"subject": "AI"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AttendanceSession.objects.count(), 1)
        self.assertEqual(AttendanceSession.objects.first().teacher, self.teacher)

    def test_student_cannot_start_session(self):
        self._auth(self.student_token)
        response = self.client.post(reverse("session-start"), {"subject": "AI"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_can_stop_own_session(self):
        self._auth(self.teacher_token)
        session = AttendanceSession.objects.create(teacher=self.teacher, subject="AI")
        response = self.client.post(reverse("session-stop", args=[session.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertEqual(session.status, AttendanceSession.STATUS_CLOSED)

    def test_teacher_cannot_stop_others_session(self):
        other_teacher = User.objects.create_user(username="prof2", password="pw12345678", role=User.ROLE_TEACHER)
        session = AttendanceSession.objects.create(teacher=other_teacher, subject="AI")
        self._auth(self.teacher_token)
        response = self.client.post(reverse("session-stop", args=[session.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test attendance.tests.test_sessions -v 2`
Expected: FAIL — `NoReverseMatch` for `"session-start"`.

- [ ] **Step 3: Write the serializers**

`backend/attendance/serializers.py`:

```python
from rest_framework import serializers
from attendance.models import AttendanceSession


class StartSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceSession
        fields = ["id", "subject", "date", "start_time", "status"]
        read_only_fields = ["id", "date", "start_time", "status"]

    def create(self, validated_data):
        return AttendanceSession.objects.create(teacher=self.context["request"].user, **validated_data)


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceSession
        fields = ["id", "subject", "date", "start_time", "end_time", "status"]
```

- [ ] **Step 4: Write the views**

`backend/attendance/views.py`:

```python
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsTeacher
from attendance.models import AttendanceSession
from attendance.serializers import SessionSerializer, StartSessionSerializer


class StartSessionView(generics.CreateAPIView):
    serializer_class = StartSessionSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeacher]


class StopSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def post(self, request, session_id):
        session = get_object_or_404(AttendanceSession, id=session_id, teacher=request.user)
        session.status = AttendanceSession.STATUS_CLOSED
        session.end_time = timezone.now()
        session.save(update_fields=["status", "end_time"])
        return Response(SessionSerializer(session).data)
```

- [ ] **Step 5: Wire URLs**

`backend/attendance/urls.py`:

```python
from django.urls import path
from attendance.views import StartSessionView, StopSessionView

urlpatterns = [
    path("sessions/start/", StartSessionView.as_view(), name="session-start"),
    path("sessions/<int:session_id>/stop/", StopSessionView.as_view(), name="session-stop"),
]
```

This file will gain more routes in Task 4/5; it isn't wired into `classpulse/urls.py` yet — that's Task 6. Tests use `reverse()`, so for THIS task's tests to pass you must temporarily wire it now: in `backend/classpulse/urls.py`, add `path("api/attendance/", include("attendance.urls"))` to `urlpatterns` (add `include` to the existing `from django.urls import path, include` if not already imported — it already is, from Phase 1's Task 3). Task 6 will not need to redo this; it only adds admin registration and confirms the full URL set once all attendance routes exist.

- [ ] **Step 6: Run test to verify it passes**

Run: `python manage.py test attendance.tests.test_sessions -v 2`
Expected: `OK` (4 tests pass).

- [ ] **Step 7: Commit**

```bash
git add backend/attendance/serializers.py backend/attendance/views.py backend/attendance/urls.py backend/attendance/tests/test_sessions.py backend/classpulse/urls.py
git commit -m "feat: teacher-only start/stop attendance session endpoints"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 4: QR token rotation endpoint

**Files:**
- Create: `backend/attendance/services.py`
- Modify: `backend/attendance/serializers.py`
- Modify: `backend/attendance/views.py`
- Modify: `backend/attendance/urls.py`
- Test: `backend/attendance/tests/test_qr.py`

- [ ] **Step 1: Write the failing test**

`backend/attendance/tests/test_qr.py`:

```python
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from attendance.models import AttendanceSession, QRToken

User = get_user_model()


class SessionQRTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.student = User.objects.create_user(username="stud", password="pw12345678", role=User.ROLE_STUDENT)
        self.session = AttendanceSession.objects.create(teacher=self.teacher, subject="AI")
        self.teacher_token = Token.objects.create(user=self.teacher)
        self.student_token = Token.objects.create(user=self.student)

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_qr_requires_teacher_role(self):
        self._auth(self.student_token)
        response = self.client.get(reverse("session-qr", args=[self.session.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_qr_issues_token(self):
        self._auth(self.teacher_token)
        response = self.client.get(reverse("session-qr", args=[self.session.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

    def test_qr_reuses_unexpired_token(self):
        self._auth(self.teacher_token)
        url = reverse("session-qr", args=[self.session.id])
        first = self.client.get(url).data["token"]
        second = self.client.get(url).data["token"]
        self.assertEqual(first, second)

    def test_qr_rotates_after_expiry(self):
        self._auth(self.teacher_token)
        url = reverse("session-qr", args=[self.session.id])
        first = self.client.get(url).data["token"]
        QRToken.objects.filter(token=first).update(expires_at=timezone.now() - timezone.timedelta(seconds=1))
        second = self.client.get(url).data["token"]
        self.assertNotEqual(first, second)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test attendance.tests.test_qr -v 2`
Expected: FAIL — `NoReverseMatch` for `"session-qr"`.

- [ ] **Step 3: Write the service**

`backend/attendance/services.py`:

```python
from attendance.models import AttendanceSession, QRToken


def get_current_qr_token(session: AttendanceSession) -> QRToken:
    latest = session.qr_tokens.order_by("-created_at").first()
    if latest and not latest.is_expired():
        return latest
    return QRToken.objects.create(session=session)
```

- [ ] **Step 4: Add the serializer**

Add to `backend/attendance/serializers.py` (append, keep existing `StartSessionSerializer`/`SessionSerializer`):

```python
from attendance.models import QRToken


class QRTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = QRToken
        fields = ["token", "expires_at"]
```

(Note: `attendance.models` import already exists at the top of the file for `AttendanceSession` — add `QRToken` to that same import line instead of a new line: `from attendance.models import AttendanceSession, QRToken`.)

- [ ] **Step 5: Add the view**

Add to `backend/attendance/views.py` (append, keep existing views):

```python
from attendance.serializers import QRTokenSerializer
from attendance.services import get_current_qr_token


class SessionQRView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request, session_id):
        session = get_object_or_404(AttendanceSession, id=session_id, teacher=request.user)
        token = get_current_qr_token(session)
        return Response(QRTokenSerializer(token).data)
```

(Merge the new import into the existing `from attendance.serializers import SessionSerializer, StartSessionSerializer` line rather than duplicating it.)

- [ ] **Step 6: Wire URL**

Add to `backend/attendance/urls.py` (append, keep existing routes):

```python
from attendance.views import SessionQRView

urlpatterns = [
    path("sessions/start/", StartSessionView.as_view(), name="session-start"),
    path("sessions/<int:session_id>/stop/", StopSessionView.as_view(), name="session-stop"),
    path("sessions/<int:session_id>/qr/", SessionQRView.as_view(), name="session-qr"),
]
```

- [ ] **Step 7: Run test to verify it passes**

Run: `python manage.py test attendance.tests.test_qr -v 2`
Expected: `OK` (4 tests pass).

- [ ] **Step 8: Commit**

```bash
git add backend/attendance/services.py backend/attendance/serializers.py backend/attendance/views.py backend/attendance/urls.py backend/attendance/tests/test_qr.py
git commit -m "feat: QR token lazy-rotation endpoint (15s expiry)"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 5: Mark attendance endpoint (full validation chain)

**Files:**
- Modify: `backend/attendance/serializers.py`
- Modify: `backend/attendance/views.py`
- Modify: `backend/attendance/urls.py`
- Test: `backend/attendance/tests/test_mark_attendance.py`

- [ ] **Step 1: Write the failing test**

`backend/attendance/tests/test_mark_attendance.py`:

```python
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from attendance.models import AttendanceSession, QRToken, Attendance

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

    def test_teacher_cannot_mark_attendance(self):
        self._auth(self.teacher_token)
        response = self.client.post(reverse("attendance-mark"), {"token": self.qr.token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_token_rejected(self):
        self._auth(self.student_token)
        response = self.client.post(reverse("attendance-mark"), {"token": "not-a-real-token"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expired_token_rejected(self):
        self.qr.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        self.qr.save()
        self._auth(self.student_token)
        response = self.client.post(reverse("attendance-mark"), {"token": self.qr.token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_attendance_rejected(self):
        self._auth(self.student_token)
        url = reverse("attendance-mark")
        self.client.post(url, {"token": self.qr.token}, format="json")
        second_qr = QRToken.objects.create(session=self.session)
        response = self.client.post(url, {"token": second_qr.token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Attendance.objects.count(), 1)

    def test_closed_session_rejected(self):
        self.session.status = AttendanceSession.STATUS_CLOSED
        self.session.save()
        self._auth(self.student_token)
        response = self.client.post(reverse("attendance-mark"), {"token": self.qr.token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test attendance.tests.test_mark_attendance -v 2`
Expected: FAIL — `NoReverseMatch` for `"attendance-mark"`.

- [ ] **Step 3: Add the serializer**

Add to `backend/attendance/serializers.py` (append; merge the `Attendance` import into the existing `from attendance.models import AttendanceSession, QRToken` line, making it `from attendance.models import AttendanceSession, QRToken, Attendance`):

```python
class MarkAttendanceSerializer(serializers.Serializer):
    token = serializers.CharField()

    def validate_token(self, value):
        try:
            qr_token = QRToken.objects.select_related("session").get(token=value)
        except QRToken.DoesNotExist:
            raise serializers.ValidationError("Invalid QR code.")
        if qr_token.session.status != AttendanceSession.STATUS_ACTIVE:
            raise serializers.ValidationError("This attendance session is closed.")
        if qr_token.is_expired():
            raise serializers.ValidationError("QR code expired. Please scan the current QR code.")
        self._qr_token = qr_token
        return value

    def validate(self, attrs):
        request = self.context["request"]
        qr_token = self._qr_token
        if Attendance.objects.filter(student=request.user, session=qr_token.session).exists():
            raise serializers.ValidationError("Attendance already marked for this session.")
        attrs["session"] = qr_token.session
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        return Attendance.objects.create(
            student=request.user,
            session=validated_data["session"],
            ip_address=request.META.get("REMOTE_ADDR"),
            device_info=request.META.get("HTTP_USER_AGENT", "")[:255],
        )
```

- [ ] **Step 4: Add the view**

Add to `backend/attendance/views.py` (append; merge the new import into the existing `from accounts.permissions import IsTeacher` line, making it `from accounts.permissions import IsTeacher, IsStudent`; merge `MarkAttendanceSerializer` into the existing serializers import line):

```python
class MarkAttendanceView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def post(self, request):
        serializer = MarkAttendanceSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        attendance = serializer.save()
        return Response({"status": "marked", "marked_at": attendance.marked_at})
```

- [ ] **Step 5: Wire URL**

Add to `backend/attendance/urls.py` (append, merge import):

```python
from attendance.views import MarkAttendanceView

urlpatterns = [
    path("sessions/start/", StartSessionView.as_view(), name="session-start"),
    path("sessions/<int:session_id>/stop/", StopSessionView.as_view(), name="session-stop"),
    path("sessions/<int:session_id>/qr/", SessionQRView.as_view(), name="session-qr"),
    path("mark/", MarkAttendanceView.as_view(), name="attendance-mark"),
]
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python manage.py test attendance.tests.test_mark_attendance -v 2`
Expected: `OK` (6 tests pass).

- [ ] **Step 7: Run the full attendance suite**

Run: `python manage.py test attendance -v 2`
Expected: `OK` (18 tests: 4 models + 4 sessions + 4 qr + 6 mark_attendance, all passing).

- [ ] **Step 8: Commit**

```bash
git add backend/attendance/serializers.py backend/attendance/views.py backend/attendance/urls.py backend/attendance/tests/test_mark_attendance.py
git commit -m "feat: mark-attendance endpoint with full server-side validation chain"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 6: Admin registration and full-suite sanity check

**Files:**
- Create: `backend/attendance/admin.py` (overwrite stock stub)
- Test: none new — this task verifies everything wired in Tasks 1-5

- [ ] **Step 1: Register models in admin**

`backend/attendance/admin.py`:

```python
from django.contrib import admin
from attendance.models import AttendanceSession, QRToken, Attendance

admin.site.register(AttendanceSession)
admin.site.register(QRToken)
admin.site.register(Attendance)
```

- [ ] **Step 2: Confirm `classpulse/urls.py` has the full picture**

Read `backend/classpulse/urls.py`. It should now look like:

```python
from django.contrib import admin
from django.urls import path, include
from accounts.views import TeacherProfileView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/student/", include("accounts.urls")),
    path("api/teacher/profile/", TeacherProfileView.as_view(), name="teacher-profile"),
    path("api/attendance/", include("attendance.urls")),
]
```

If the `path("api/attendance/", include("attendance.urls"))` line isn't there (it should already be, added in Task 3 Step 5), add it now.

- [ ] **Step 3: Run the full backend test suite**

Run: `python manage.py test -v 2`
Expected: `OK` — all `accounts` tests (11 from Phase 1) plus all `attendance` tests (from Task 2-5) pass, no failures, no errors.

- [ ] **Step 4: Commit**

```bash
git add backend/attendance/admin.py backend/classpulse/urls.py
git commit -m "feat: register attendance models in admin"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 7: Frontend API client additions

**Files:**
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add the new types and functions**

Add to `frontend/src/api/client.ts` (append at the end of the file, after the existing `logout` function; keep all existing exports untouched):

```ts
export interface SessionResponse {
  id: number;
  subject: string;
  date: string;
  start_time: string;
  end_time?: string | null;
  status: "active" | "closed";
}

export interface QRTokenResponse {
  token: string;
  expires_at: string;
}

export async function startSession(subject: string): Promise<SessionResponse> {
  const { data } = await api.post<SessionResponse>("/attendance/sessions/start/", { subject });
  return data;
}

export async function stopSession(sessionId: number): Promise<SessionResponse> {
  const { data } = await api.post<SessionResponse>(`/attendance/sessions/${sessionId}/stop/`);
  return data;
}

export async function getSessionQR(sessionId: number): Promise<QRTokenResponse> {
  const { data } = await api.get<QRTokenResponse>(`/attendance/sessions/${sessionId}/qr/`);
  return data;
}

export async function markAttendance(token: string) {
  const { data } = await api.post("/attendance/mark/", { token });
  return data;
}
```

- [ ] **Step 2: Verify it compiles**

Run `npm run build` from `frontend/`. Expected: no TypeScript errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat: frontend API client for sessions, QR, and mark-attendance"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 8: Teacher pages — start attendance and live QR

**Files:**
- Create: `frontend/src/pages/teacher/StartAttendancePage.tsx`
- Create: `frontend/src/pages/teacher/LiveQRPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/TeacherProfilePage.tsx`

- [ ] **Step 1: Install the QR rendering library**

Run (from `frontend/`): `npm install qrcode.react`

- [ ] **Step 2: Start-attendance page**

`frontend/src/pages/teacher/StartAttendancePage.tsx`:

```tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Container, Form, Button, Alert } from "react-bootstrap";
import { startSession } from "../../api/client";

export default function StartAttendancePage() {
  const [subject, setSubject] = useState("");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const session = await startSession(subject);
      navigate(`/teacher/session/${session.id}`);
    } catch {
      setError("Could not start attendance session.");
    }
  };

  return (
    <Container className="py-4" style={{ maxWidth: 400 }}>
      <h2>Start Attendance</h2>
      {error && <Alert variant="danger">{error}</Alert>}
      <Form onSubmit={handleSubmit}>
        <Form.Group className="mb-3" controlId="subject">
          <Form.Label>Subject</Form.Label>
          <Form.Control value={subject} onChange={(e) => setSubject(e.target.value)} required />
        </Form.Group>
        <Button type="submit">Start</Button>
      </Form>
    </Container>
  );
}
```

- [ ] **Step 3: Live QR page**

`frontend/src/pages/teacher/LiveQRPage.tsx`:

```tsx
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Container, Button, Spinner } from "react-bootstrap";
import { QRCodeSVG } from "qrcode.react";
import { getSessionQR, stopSession } from "../../api/client";

const QR_REFRESH_MS = 15000;

export default function LiveQRPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    const id = Number(sessionId);
    const fetchToken = () => {
      getSessionQR(id).then((data) => setToken(data.token));
    };
    fetchToken();
    const interval = setInterval(fetchToken, QR_REFRESH_MS);
    return () => clearInterval(interval);
  }, [sessionId]);

  const handleStop = async () => {
    if (!sessionId) return;
    await stopSession(Number(sessionId));
    navigate("/teacher/profile");
  };

  return (
    <Container className="py-4 text-center">
      <h2>Attendance Live</h2>
      {token ? <QRCodeSVG value={token} size={256} /> : <Spinner animation="border" />}
      <p className="mt-3 text-muted">QR refreshes every 15 seconds</p>
      <Button variant="danger" onClick={handleStop}>
        Stop Attendance
      </Button>
    </Container>
  );
}
```

- [ ] **Step 4: Add routes to App.tsx**

Read `frontend/src/App.tsx` first — it currently has routes for `/`, `/register`, `/login`, and inside a `<ProtectedRoute>` block: `/student/profile` and `/teacher/profile`, then a catch-all `path="*"` last. Add two new imports and two new routes INSIDE the `<ProtectedRoute>` block, before the catch-all route (which must stay last):

Add imports:
```tsx
import StartAttendancePage from "./pages/teacher/StartAttendancePage";
import LiveQRPage from "./pages/teacher/LiveQRPage";
```

Add routes (inside `<Route element={<ProtectedRoute />}>...</Route>`, alongside the existing `/student/profile` and `/teacher/profile` routes):
```tsx
<Route path="/teacher/start-attendance" element={<StartAttendancePage />} />
<Route path="/teacher/session/:sessionId" element={<LiveQRPage />} />
```

- [ ] **Step 5: Add a link from TeacherProfilePage**

In `frontend/src/pages/TeacherProfilePage.tsx`, add `import { Link } from "react-router-dom";` to the imports, and add a link after the existing `<p>Email: {profile.email}</p>` line (immediately before the closing `</Container>`):

```tsx
<Link to="/teacher/start-attendance" className="btn btn-primary">
  Start Attendance
</Link>
```

- [ ] **Step 6: Verify it builds**

Run `npm run build` from `frontend/`. Expected: no TypeScript errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/teacher frontend/src/App.tsx frontend/src/pages/TeacherProfilePage.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat: teacher start-attendance and live QR pages"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 9: Student page — scan QR

**Files:**
- Create: `frontend/src/pages/student/ScanQRPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/StudentProfilePage.tsx`

- [ ] **Step 1: Install the QR scanning library**

Run (from `frontend/`): `npm install html5-qrcode`

- [ ] **Step 2: Scan page**

`frontend/src/pages/student/ScanQRPage.tsx`:

```tsx
import { useEffect, useRef, useState } from "react";
import { Container, Alert } from "react-bootstrap";
import { Html5Qrcode } from "html5-qrcode";
import { markAttendance } from "../../api/client";

const SCANNER_ELEMENT_ID = "qr-scanner";

export default function ScanQRPage() {
  const [message, setMessage] = useState<{ type: "success" | "danger"; text: string } | null>(null);
  const scanningRef = useRef(false);

  useEffect(() => {
    const scanner = new Html5Qrcode(SCANNER_ELEMENT_ID);

    scanner
      .start(
        { facingMode: "environment" },
        { fps: 10, qrbox: 250 },
        async (decodedText) => {
          if (scanningRef.current) return;
          scanningRef.current = true;
          try {
            await markAttendance(decodedText);
            setMessage({ type: "success", text: "Attendance marked!" });
          } catch (err: any) {
            const data = err?.response?.data;
            const detail = data?.token?.[0] || data?.non_field_errors?.[0] || "Could not mark attendance.";
            setMessage({ type: "danger", text: detail });
          } finally {
            setTimeout(() => {
              scanningRef.current = false;
            }, 2000);
          }
        },
        () => {}
      )
      .catch(() => {
        setMessage({ type: "danger", text: "Could not access camera." });
      });

    return () => {
      scanner.stop().catch(() => {});
    };
  }, []);

  return (
    <Container className="py-4">
      <h2>Scan Attendance QR</h2>
      {message && <Alert variant={message.type}>{message.text}</Alert>}
      <div id={SCANNER_ELEMENT_ID} style={{ width: "100%", maxWidth: 400 }} />
    </Container>
  );
}
```

- [ ] **Step 3: Add route to App.tsx**

Add import: `import ScanQRPage from "./pages/student/ScanQRPage";`

Add route (inside the `<ProtectedRoute>` block, alongside the other protected routes, before the catch-all):
```tsx
<Route path="/student/scan" element={<ScanQRPage />} />
```

- [ ] **Step 4: Add a link from StudentProfilePage**

In `frontend/src/pages/StudentProfilePage.tsx`, add `import { Link } from "react-router-dom";` to the imports, and add a link after the existing `<p>Email: {profile.email}</p>` line (immediately before the closing `</Container>`):

```tsx
<Link to="/student/scan" className="btn btn-primary mt-2">
  Scan Attendance QR
</Link>
```

- [ ] **Step 5: Verify it builds**

Run `npm run build` from `frontend/`. Expected: no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/student frontend/src/App.tsx frontend/src/pages/StudentProfilePage.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat: student QR scan page"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Phase 2 Exit Criteria (from docs/plan.md)

- [ ] Teacher starts a session, QR visibly changes every 15 seconds (verified via `getSessionQR` polling and the `test_qr_rotates_after_expiry` test).
- [ ] A student scan within the 15s window marks attendance once (verified via `test_student_can_mark_attendance`).
- [ ] A stale QR is rejected (`test_expired_token_rejected`).
- [ ] A second scan is rejected as duplicate, enforced at the DB level (`test_duplicate_attendance_rejected`, `UniqueConstraint` on `(student, session)`).
- [ ] All validation is server-side (`MarkAttendanceSerializer` runs the full chain; client never decides validity).

## After Completion

Update the Work Log in [`Agent.md`](../../../Agent.md) with a new entry noting Phase 2 is complete, then write Phase 3's detailed plan (`docs/plan.md`'s Real-Time Dashboard phase) the same way.
