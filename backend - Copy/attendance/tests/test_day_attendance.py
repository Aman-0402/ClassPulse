from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from accounts.models import StudentProfile
from attendance.models import AttendanceSession, Attendance
from attendance.services import get_day_attendance

User = get_user_model()


class DayAttendanceServiceTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.s1 = User.objects.create_user(
            username="stud1", password="pw12345678", role=User.ROLE_STUDENT, first_name="Aman Raj"
        )
        StudentProfile.objects.create(user=self.s1, crn="101", urn="urn101", course="BBA", semester=3, section="D")
        self.s2 = User.objects.create_user(
            username="stud2", password="pw12345678", role=User.ROLE_STUDENT, first_name="Priya Singh"
        )
        StudentProfile.objects.create(user=self.s2, crn="102", course="BBA", semester=3, section="D")
        # Different section — must never appear in a "D" query.
        self.s3 = User.objects.create_user(username="stud3", password="pw12345678", role=User.ROLE_STUDENT)
        StudentProfile.objects.create(user=self.s3, crn="201", course="BBA", semester=3, section="E")

        self.date = timezone.localdate()
        self.session = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI Training", section="D", date=self.date
        )
        Attendance.objects.create(student=self.s1, session=self.session)

    def test_only_section_students_included(self):
        _, rows = get_day_attendance("D", self.date)
        self.assertEqual({r["crn"] for r in rows}, {"101", "102"})

    def test_present_and_absent_flagged_correctly(self):
        _, rows = get_day_attendance("D", self.date)
        by_crn = {r["crn"]: r for r in rows}
        self.assertTrue(by_crn["101"]["present"])
        self.assertFalse(by_crn["102"]["present"])

    def test_roll_number_is_urn(self):
        _, rows = get_day_attendance("D", self.date)
        by_crn = {r["crn"]: r for r in rows}
        self.assertEqual(by_crn["101"]["roll_number"], "urn101")

    def test_no_session_that_day_still_lists_students_all_absent(self):
        sessions, rows = get_day_attendance("D", self.date - timezone.timedelta(days=1))
        self.assertEqual(sessions, [])
        self.assertTrue(all(not r["present"] for r in rows))


class DayAttendanceViewTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.token = Token.objects.create(user=self.teacher)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        self.s1 = User.objects.create_user(username="stud1", password="pw12345678", role=User.ROLE_STUDENT)
        StudentProfile.objects.create(user=self.s1, crn="101", course="BBA", semester=3, section="D")

        self.date = timezone.localdate()
        self.session = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI Training", section="D", date=self.date
        )
        Attendance.objects.create(student=self.s1, session=self.session)

    def test_requires_section_and_date(self):
        response = self.client.get(reverse("day-attendance"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_date_rejected(self):
        response = self.client.get(reverse("day-attendance"), {"section": "D", "date": "not-a-date"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_returns_day_attendance_for_section(self):
        response = self.client.get(
            reverse("day-attendance"), {"section": "D", "date": self.date.isoformat()}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["present_count"], 1)
        self.assertEqual(response.data["total_students"], 1)
        self.assertEqual(len(response.data["sessions"]), 1)

    def test_student_cannot_access(self):
        student = User.objects.create_user(username="stud0", password="pw12345678", role=User.ROLE_STUDENT)
        student_token = Token.objects.create(user=student)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {student_token.key}")
        response = self.client.get(
            reverse("day-attendance"), {"section": "D", "date": self.date.isoformat()}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
