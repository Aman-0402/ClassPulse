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
