from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from attendance.models import AttendanceSession, Attendance

User = get_user_model()


class StudentHistoryTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.student = User.objects.create_user(username="stud", password="pw12345678", role=User.ROLE_STUDENT)
        self.teacher_token = Token.objects.create(user=self.teacher)
        self.student_token = Token.objects.create(user=self.student)
        self.closed1 = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI", status=AttendanceSession.STATUS_CLOSED
        )
        self.closed2 = AttendanceSession.objects.create(
            teacher=self.teacher, subject="DS", status=AttendanceSession.STATUS_CLOSED
        )
        AttendanceSession.objects.create(teacher=self.teacher, subject="AI", status=AttendanceSession.STATUS_ACTIVE)
        Attendance.objects.create(student=self.student, session=self.closed1)

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_requires_student_role(self):
        self._auth(self.teacher_token)
        response = self.client.get(reverse("student-attendance-history"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_correct_totals_and_history(self):
        self._auth(self.student_token)
        response = self.client.get(reverse("student-attendance-history"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 2)
        self.assertEqual(response.data["present"], 1)
        self.assertEqual(response.data["percentage"], 50.0)
        self.assertEqual(len(response.data["history"]), 2)
        statuses = {h["subject"]: h["status"] for h in response.data["history"]}
        self.assertIn("present", statuses.values())
        self.assertIn("absent", statuses.values())
