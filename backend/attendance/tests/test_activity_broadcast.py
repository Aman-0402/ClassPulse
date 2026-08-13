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
    def test_wrong_section_broadcasts_activity_event(self, mock_get_layer):
        from accounts.models import StudentProfile

        StudentProfile.objects.create(user=self.student, crn="101", course="BBA", semester=3, section="B")
        self.session.section = "A"
        self.session.save()
        mock_layer = AsyncMock()
        mock_get_layer.return_value = mock_layer
        self._auth()

        self.client.post(reverse("attendance-mark"), {"token": self.qr.token}, format="json")

        mock_layer.group_send.assert_called_once()
        group_name, event = mock_layer.group_send.call_args[0]
        self.assertEqual(group_name, f"attendance_session_{self.session.id}")
        self.assertEqual(event["type"], "activity.update")
        self.assertEqual(event["data"]["activity_type"], "wrong_section")

    @patch("attendance.services.get_channel_layer")
    def test_successful_mark_broadcasts_attendance_not_activity(self, mock_get_layer):
        mock_layer = AsyncMock()
        mock_get_layer.return_value = mock_layer
        self._auth()

        self.client.post(reverse("attendance-mark"), {"token": self.qr.token}, format="json")

        mock_layer.group_send.assert_called_once()
        _, event = mock_layer.group_send.call_args[0]
        self.assertEqual(event["type"], "attendance.update")
