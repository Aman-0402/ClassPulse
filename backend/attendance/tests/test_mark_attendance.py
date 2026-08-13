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

    def test_student_from_wrong_section_rejected_and_logged(self):
        from accounts.models import StudentProfile

        StudentProfile.objects.create(user=self.student, crn="101", course="BBA", semester=3, section="B")
        self.session.section = "A"
        self.session.save()
        self._auth(self.student_token)
        response = self.client.post(reverse("attendance-mark"), {"token": self.qr.token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Section A", response.data["detail"])
        self.assertEqual(Attendance.objects.count(), 0)
        self.assertEqual(ActivityLog.objects.filter(activity_type=ActivityLog.TYPE_WRONG_SECTION).count(), 1)

    def test_student_from_correct_section_allowed(self):
        from accounts.models import StudentProfile

        StudentProfile.objects.create(user=self.student, crn="101", course="BBA", semester=3, section="A")
        self.session.section = "A"
        self.session.save()
        self._auth(self.student_token)
        response = self.client.post(reverse("attendance-mark"), {"token": self.qr.token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Attendance.objects.count(), 1)

    def test_sessionless_of_section_allows_any_student(self):
        # session.section defaults to "" (e.g. started without picking a timetable slot) —
        # no section restriction should apply in that case.
        self._auth(self.student_token)
        response = self.client.post(reverse("attendance-mark"), {"token": self.qr.token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_expired_attendance_window_auto_closes_and_rejects(self):
        self.session.duration_minutes = 5
        self.session.start_time = timezone.now() - timezone.timedelta(minutes=6)
        self.session.save()
        self._auth(self.student_token)
        response = self.client.post(reverse("attendance-mark"), {"token": self.qr.token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, AttendanceSession.STATUS_CLOSED)
        self.assertEqual(ActivityLog.objects.filter(activity_type=ActivityLog.TYPE_SESSION_CLOSED).count(), 1)
