from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
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

    def test_start_session_defaults_duration_to_5_minutes(self):
        self._auth(self.teacher_token)
        response = self.client.post(reverse("session-start"), {"subject": "AI"}, format="json")
        self.assertEqual(response.data["duration_minutes"], 5)

    def test_teacher_can_set_custom_duration(self):
        self._auth(self.teacher_token)
        response = self.client.post(
            reverse("session-start"), {"subject": "AI", "duration_minutes": 15}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = AttendanceSession.objects.get()
        self.assertEqual(session.duration_minutes, 15)

    def test_duration_out_of_range_rejected(self):
        self._auth(self.teacher_token)
        response = self.client.post(
            reverse("session-start"), {"subject": "AI", "duration_minutes": 200}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_start_session_defaults_periods_to_1(self):
        self._auth(self.teacher_token)
        response = self.client.post(reverse("session-start"), {"subject": "AI"}, format="json")
        self.assertEqual(response.data["periods"], 1)

    def test_teacher_can_start_merged_double_period_session(self):
        self._auth(self.teacher_token)
        response = self.client.post(
            reverse("session-start"), {"subject": "AI", "periods": 2}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AttendanceSession.objects.get().periods, 2)

    def test_periods_out_of_range_rejected(self):
        self._auth(self.teacher_token)
        response = self.client.post(reverse("session-start"), {"subject": "AI", "periods": 3}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_cannot_start_session(self):
        self._auth(self.student_token)
        response = self.client.post(reverse("session-start"), {"subject": "AI"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_restarting_same_section_same_day_reuses_session_not_a_second_one(self):
        # Reported bug: start -> stop -> start again (same section, same day) was
        # creating a second AttendanceSession row, silently doubling both the
        # attendance total and, for a partially-attending student, their present
        # count too — build_attendance_matrix() sums periods across every closed
        # session with no per-day dedup. There must only ever be one row.
        self._auth(self.teacher_token)
        first = self.client.post(
            reverse("session-start"), {"subject": "AI", "section": "A"}, format="json"
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        first_id = first.data["id"]

        self.client.post(reverse("session-stop", args=[first_id]))

        second = self.client.post(
            reverse("session-start"), {"subject": "AI", "section": "A"}, format="json"
        )
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)

        self.assertEqual(AttendanceSession.objects.count(), 1)
        self.assertEqual(second.data["id"], first_id)
        reused = AttendanceSession.objects.get(id=first_id)
        self.assertEqual(reused.status, AttendanceSession.STATUS_ACTIVE)

    def test_restarting_different_section_same_day_creates_a_new_session(self):
        self._auth(self.teacher_token)
        first = self.client.post(
            reverse("session-start"), {"subject": "AI", "section": "A"}, format="json"
        )
        self.client.post(reverse("session-stop", args=[first.data["id"]]))

        second = self.client.post(
            reverse("session-start"), {"subject": "AI", "section": "B"}, format="json"
        )
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AttendanceSession.objects.count(), 2)
        self.assertNotEqual(second.data["id"], first.data["id"])

    def test_sessions_without_a_section_are_never_deduped(self):
        self._auth(self.teacher_token)
        first = self.client.post(reverse("session-start"), {"subject": "AI"}, format="json")
        self.client.post(reverse("session-stop", args=[first.data["id"]]))

        second = self.client.post(reverse("session-start"), {"subject": "AI"}, format="json")
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AttendanceSession.objects.count(), 2)

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

    def test_stopping_already_closed_session_rejected(self):
        self._auth(self.teacher_token)
        session = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI", status=AttendanceSession.STATUS_CLOSED
        )
        original_end_time = session.end_time
        response = self.client.post(reverse("session-stop", args=[session.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        session.refresh_from_db()
        self.assertEqual(session.end_time, original_end_time)

    def test_teacher_can_resume_closed_session(self):
        self._auth(self.teacher_token)
        session = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI", status=AttendanceSession.STATUS_CLOSED, duration_minutes=5
        )
        response = self.client.post(reverse("session-resume", args=[session.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertEqual(session.status, AttendanceSession.STATUS_ACTIVE)
        self.assertIsNone(session.end_time)
        self.assertFalse(session.is_window_expired())

    def test_resuming_auto_expired_session_reopens_the_window(self):
        # The exact scenario reported: window auto-expires after 5 min, teacher
        # clicks back in — resuming must give a genuinely fresh window, not one
        # that's still expired relative to the old start_time.
        self._auth(self.teacher_token)
        session = AttendanceSession.objects.create(
            teacher=self.teacher,
            subject="AI",
            duration_minutes=5,
            start_time=timezone.now() - timezone.timedelta(minutes=10),
        )
        session.status = AttendanceSession.STATUS_CLOSED
        session.save()
        self.client.post(reverse("session-resume", args=[session.id]))
        session.refresh_from_db()
        self.assertFalse(session.is_window_expired())

    def test_resuming_already_active_session_rejected(self):
        self._auth(self.teacher_token)
        session = AttendanceSession.objects.create(teacher=self.teacher, subject="AI")
        response = self.client.post(reverse("session-resume", args=[session.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_teacher_cannot_resume_others_session(self):
        other_teacher = User.objects.create_user(username="prof3", password="pw12345678", role=User.ROLE_TEACHER)
        session = AttendanceSession.objects.create(
            teacher=other_teacher, subject="AI", status=AttendanceSession.STATUS_CLOSED
        )
        self._auth(self.teacher_token)
        response = self.client.post(reverse("session-resume", args=[session.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_resuming_preserves_existing_attendance(self):
        from accounts.models import StudentProfile
        from attendance.models import Attendance

        StudentProfile.objects.create(user=self.student, crn="101", course="BBA", semester=3, section="A")
        session = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI", section="A", status=AttendanceSession.STATUS_CLOSED
        )
        Attendance.objects.create(student=self.student, session=session)
        self._auth(self.teacher_token)
        self.client.post(reverse("session-resume", args=[session.id]))
        self.assertEqual(Attendance.objects.filter(session=session).count(), 1)
