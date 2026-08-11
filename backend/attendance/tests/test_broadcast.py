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
