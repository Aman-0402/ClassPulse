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
