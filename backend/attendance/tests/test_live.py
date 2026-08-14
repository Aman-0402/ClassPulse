from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from accounts.models import StudentProfile
from attendance.models import AttendanceSession, Attendance, QRToken

User = get_user_model()


class SessionLiveTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.student = User.objects.create_user(
            username="stud", password="pw12345678", role=User.ROLE_STUDENT, first_name="Aman Raj"
        )
        self.student_token = Token.objects.create(user=self.student)
        self.teacher_token = Token.objects.create(user=self.teacher)
        self.session = AttendanceSession.objects.create(teacher=self.teacher, subject="AI")

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_requires_teacher_role(self):
        self._auth(self.student_token)
        response = self.client.get(reverse("session-live", args=[self.session.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_present_count_and_recent(self):
        Attendance.objects.create(student=self.student, session=self.session)
        self._auth(self.teacher_token)
        response = self.client.get(reverse("session-live", args=[self.session.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["present_count"], 1)
        self.assertEqual(len(response.data["recent"]), 1)
        self.assertEqual(response.data["recent"][0]["name"], "Aman Raj")

    def test_other_teacher_cannot_view(self):
        other_teacher = User.objects.create_user(
            username="prof2", password="pw12345678", role=User.ROLE_TEACHER
        )
        other_token = Token.objects.create(user=other_teacher)
        self._auth(other_token)
        response = self.client.get(reverse("session-live", args=[self.session.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_sectionless_session_has_empty_roster(self):
        self._auth(self.teacher_token)
        response = self.client.get(reverse("session-live", args=[self.session.id]))
        self.assertEqual(response.data["roster"], [])


class SessionRosterTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.teacher_token = Token.objects.create(user=self.teacher)

        self.s1 = User.objects.create_user(
            username="stud1", password="pw12345678", role=User.ROLE_STUDENT, first_name="Aman Raj"
        )
        StudentProfile.objects.create(user=self.s1, crn="101", urn="urn101", course="BBA", semester=3, section="D")
        self.s2 = User.objects.create_user(
            username="stud2", password="pw12345678", role=User.ROLE_STUDENT, first_name="Priya Singh"
        )
        StudentProfile.objects.create(user=self.s2, crn="102", urn="urn102", course="BBA", semester=3, section="D")
        # Different section — must never appear in a "D" session's roster.
        self.s3 = User.objects.create_user(username="stud3", password="pw12345678", role=User.ROLE_STUDENT)
        StudentProfile.objects.create(user=self.s3, crn="201", urn="urn201", course="BBA", semester=3, section="E")

        self.session = AttendanceSession.objects.create(teacher=self.teacher, subject="AI Training", section="D")
        Attendance.objects.create(student=self.s1, session=self.session)

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_roster_scoped_to_section_and_present_status(self):
        self._auth(self.teacher_token)
        response = self.client.get(reverse("session-live", args=[self.session.id]))
        roster = response.data["roster"]
        self.assertEqual({r["crn"] for r in roster}, {"101", "102"})
        by_crn = {r["crn"]: r for r in roster}
        self.assertTrue(by_crn["101"]["present"])
        self.assertFalse(by_crn["102"]["present"])
        self.assertEqual(by_crn["101"]["roll_number"], "urn101")

    def test_roster_scoped_to_this_session_not_whole_day(self):
        # A second session that day for the same section must not leak into this
        # session's roster — get_session_roster is per-session, not per-day.
        other_session = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI Training", section="D", date=self.session.date
        )
        Attendance.objects.create(student=self.s2, session=other_session)
        self._auth(self.teacher_token)
        response = self.client.get(reverse("session-live", args=[self.session.id]))
        by_crn = {r["crn"]: r for r in response.data["roster"]}
        self.assertFalse(by_crn["102"]["present"])
