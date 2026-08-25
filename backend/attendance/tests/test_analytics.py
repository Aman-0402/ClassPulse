import datetime

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
        StudentProfile.objects.create(user=self.s1, crn="101", urn="urn101", course="CSE", semester=5, section="A")
        self.s2 = User.objects.create_user(
            username="stud2", password="pw12345678", role=User.ROLE_STUDENT, first_name="Priya Singh"
        )
        StudentProfile.objects.create(user=self.s2, crn="102", course="CSE", semester=5, section="A")

        self.s3 = User.objects.create_user(
            username="stud3", password="pw12345678", role=User.ROLE_STUDENT, first_name="Ravi Kumar"
        )
        StudentProfile.objects.create(user=self.s3, crn="201", course="CSE", semester=5, section="B")

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
        self.assertEqual(response.data["total_students"], 3)
        self.assertEqual(len(response.data["students"]), 3)

    def test_available_sections_lists_all_distinct_sections(self):
        self._auth(self.teacher_token)
        response = self.client.get(reverse("attendance-analytics"))
        self.assertEqual(response.data["available_sections"], ["A", "B"])
        self.assertEqual(response.data["section"], "")

    def test_section_filter_scopes_students_and_totals(self):
        self._auth(self.teacher_token)
        response = self.client.get(reverse("attendance-analytics"), {"section": "B"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["section"], "B")
        self.assertEqual(response.data["total_students"], 1)
        self.assertEqual(response.data["students"][0]["crn"], "201")

    def test_below_threshold_list(self):
        self._auth(self.teacher_token)
        response = self.client.get(reverse("attendance-analytics"))
        below_crns = {s["crn"] for s in response.data["below_threshold"]}
        self.assertEqual(below_crns, {"102", "201"})

    def test_students_include_roll_number(self):
        self._auth(self.teacher_token)
        response = self.client.get(reverse("attendance-analytics"))
        by_crn = {s["crn"]: s for s in response.data["students"]}
        self.assertEqual(by_crn["101"]["roll_number"], "urn101")

    def test_overall_rate_weighted_by_merged_session_periods(self):
        # closed1 is a merged double period (periods=2); closed2 is a normal single period.
        # Weighted total per student = 2 + 1 = 3, so with 3 students the denominator is 9,
        # not len(sessions)*students = 2*3 = 6 — a session count would silently overcount the rate.
        self.closed1.periods = 2
        self.closed1.save()
        self._auth(self.teacher_token)
        response = self.client.get(reverse("attendance-analytics"))
        # present: s1 present both (2+1=3), s2 present closed1 only (2), s3 absent (0) -> 5 present / 9 possible
        self.assertEqual(response.data["overall_rate"], round(5 / 9 * 100, 1))


class AnalyticsDateRangeTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.teacher_token = Token.objects.create(user=self.teacher)
        self.student = User.objects.create_user(
            username="stud1", password="pw12345678", role=User.ROLE_STUDENT, first_name="Aman Raj"
        )
        StudentProfile.objects.create(user=self.student, crn="101", urn="urn101", course="BBA", semester=3, section="A")

        self.old_session = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI", status=AttendanceSession.STATUS_CLOSED,
            date=datetime.date(2026, 1, 5),
        )
        self.recent_session = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI", status=AttendanceSession.STATUS_CLOSED,
            date=datetime.date(2026, 8, 10),
        )
        Attendance.objects.create(student=self.student, session=self.old_session)
        Attendance.objects.create(student=self.student, session=self.recent_session)

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_no_range_includes_all_sessions(self):
        self._auth(self.teacher_token)
        response = self.client.get(reverse("attendance-analytics"))
        self.assertEqual(response.data["total_sessions"], 2)

    def test_date_range_scopes_to_recent_session_only(self):
        self._auth(self.teacher_token)
        response = self.client.get(
            reverse("attendance-analytics"), {"date_from": "2026-08-01", "date_to": "2026-08-31"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_sessions"], 1)
        self.assertEqual(response.data["students"][0]["total"], 1)
        self.assertEqual(response.data["students"][0]["present"], 1)

    def test_invalid_date_format_rejected(self):
        self._auth(self.teacher_token)
        response = self.client.get(reverse("attendance-analytics"), {"date_from": "not-a-date"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
