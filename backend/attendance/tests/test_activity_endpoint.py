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
