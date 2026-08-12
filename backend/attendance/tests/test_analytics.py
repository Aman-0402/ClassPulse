from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from accounts.models import StudentProfile
from attendance.models import AttendanceSession, Attendance

User = get_user_model()


class AnalyticsTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.teacher_token = Token.objects.create(user=self.teacher)
        self.student_token = Token.objects.create(
            user=User.objects.create_user(username="stud0", password="pw12345678", role=User.ROLE_STUDENT)
        )

        self.s1 = User.objects.create_user(
            username="stud1", password="pw12345678", role=User.ROLE_STUDENT, first_name="Aman Raj"
        )
        StudentProfile.objects.create(user=self.s1, crn="101", course="CSE", semester=5, section="A")
        self.s2 = User.objects.create_user(
            username="stud2", password="pw12345678", role=User.ROLE_STUDENT, first_name="Priya Singh"
        )
        StudentProfile.objects.create(user=self.s2, crn="102", course="CSE", semester=5, section="A")

        self.closed1 = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI", status=AttendanceSession.STATUS_CLOSED
        )
        self.closed2 = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI", status=AttendanceSession.STATUS_CLOSED
        )
        Attendance.objects.create(student=self.s1, session=self.closed1)
        Attendance.objects.create(student=self.s1, session=self.closed2)
        Attendance.objects.create(student=self.s2, session=self.closed1)

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_requires_teacher_role(self):
        self._auth(self.student_token)
        response = self.client.get(reverse("attendance-analytics"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_overall_and_per_student_breakdown(self):
        self._auth(self.teacher_token)
        response = self.client.get(reverse("attendance-analytics"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_sessions"], 2)
        self.assertEqual(response.data["total_students"], 2)
        self.assertEqual(response.data["overall_rate"], 75.0)
        self.assertEqual(len(response.data["students"]), 2)

    def test_below_threshold_list(self):
        self._auth(self.teacher_token)
        response = self.client.get(reverse("attendance-analytics"))
        below = response.data["below_threshold"]
        self.assertEqual(len(below), 1)
        self.assertEqual(below[0]["crn"], "102")
