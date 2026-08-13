from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from accounts.models import StudentProfile
from attendance.models import AttendanceSession, Attendance

User = get_user_model()


class ManualAttendanceTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.teacher_token = Token.objects.create(user=self.teacher)
        self.student = User.objects.create_user(username="stud1", password="pw12345678", role=User.ROLE_STUDENT)
        StudentProfile.objects.create(user=self.student, crn="101", course="BBA", semester=3, section="D")
        self.other_section_student = User.objects.create_user(
            username="stud2", password="pw12345678", role=User.ROLE_STUDENT
        )
        StudentProfile.objects.create(
            user=self.other_section_student, crn="201", course="BBA", semester=3, section="E"
        )
        self.session = AttendanceSession.objects.create(teacher=self.teacher, subject="AI Training", section="D")

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_teacher_can_mark_present(self):
        self._auth(self.teacher_token)
        response = self.client.post(
            reverse("session-manual-attendance", args=[self.session.id]),
            {"crn": "101", "present": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Attendance.objects.filter(student=self.student, session=self.session).exists())

    def test_teacher_can_mark_absent_removes_record(self):
        Attendance.objects.create(student=self.student, session=self.session)
        self._auth(self.teacher_token)
        response = self.client.post(
            reverse("session-manual-attendance", args=[self.session.id]),
            {"crn": "101", "present": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Attendance.objects.filter(student=self.student, session=self.session).exists())

    def test_marking_present_twice_does_not_duplicate(self):
        self._auth(self.teacher_token)
        url = reverse("session-manual-attendance", args=[self.session.id])
        self.client.post(url, {"crn": "101", "present": True}, format="json")
        response = self.client.post(url, {"crn": "101", "present": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Attendance.objects.filter(student=self.student, session=self.session).count(), 1)

    def test_wrong_section_student_rejected(self):
        self._auth(self.teacher_token)
        response = self.client.post(
            reverse("session-manual-attendance", args=[self.session.id]),
            {"crn": "201", "present": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Attendance.objects.filter(student=self.other_section_student, session=self.session).exists())

    def test_missing_present_field_rejected(self):
        self._auth(self.teacher_token)
        response = self.client.post(
            reverse("session-manual-attendance", args=[self.session.id]), {"crn": "101"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_crn_rejected(self):
        self._auth(self.teacher_token)
        response = self.client.post(
            reverse("session-manual-attendance", args=[self.session.id]),
            {"crn": "does-not-exist", "present": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_teacher_cannot_override_others_session(self):
        other_teacher = User.objects.create_user(username="prof2", password="pw12345678", role=User.ROLE_TEACHER)
        other_session = AttendanceSession.objects.create(teacher=other_teacher, subject="AI Training", section="D")
        self._auth(self.teacher_token)
        response = self.client.post(
            reverse("session-manual-attendance", args=[other_session.id]),
            {"crn": "101", "present": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_student_cannot_access(self):
        student_token = Token.objects.create(user=self.student)
        self._auth(student_token)
        response = self.client.post(
            reverse("session-manual-attendance", args=[self.session.id]),
            {"crn": "101", "present": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
