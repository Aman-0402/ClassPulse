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
