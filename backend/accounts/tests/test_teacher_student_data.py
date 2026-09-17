from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import StudentProfile, StudentScanPolicy
from attendance.models import Attendance, AttendanceSession

User = get_user_model()


class TeacherStudentDataTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="admin", password="pw12345678", role=User.ROLE_TEACHER)
        self.student_a = User.objects.create_user(
            username="25BBA001", password="oldpass123", first_name="Anaya Rao", email="a@example.com",
            role=User.ROLE_STUDENT,
        )
        self.student_b = User.objects.create_user(
            username="25BBA002", password="oldpass123", first_name="Bhavya Sen", email="b@example.com",
            role=User.ROLE_STUDENT,
        )
        StudentProfile.objects.create(
            user=self.student_a, crn="25BBA001", urn="1", course="BBA", semester=3, section="A",
            contact_number="9876543210",
        )
        StudentProfile.objects.create(
            user=self.student_b, crn="25BBA002", urn="2", course="BBA", semester=3, section="B"
        )
        self.session = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI Training", section="A", date=timezone.localdate()
        )
        Attendance.objects.create(student=self.student_a, session=self.session, ip_address="127.0.0.1")
        self.teacher_token = Token.objects.create(user=self.teacher)
        self.student_token = Token.objects.create(user=self.student_a)

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_teacher_can_filter_students_by_section(self):
        self._auth(self.teacher_token)
        response = self.client.get(reverse("teacher-student-data"), {"section": "A"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["sections"], ["A", "B"])
        self.assertFalse(response.data["profile_scan_lock_enabled"])
        self.assertEqual(len(response.data["students"]), 1)
        self.assertEqual(response.data["students"][0]["crn"], "25BBA001")
        self.assertFalse(response.data["students"][0]["scan_profile_complete"])
        self.assertIn("profile photo", response.data["students"][0]["missing_scan_profile_fields"])

    def test_teacher_student_data_defaults_to_first_section(self):
        self._auth(self.teacher_token)
        response = self.client.get(reverse("teacher-student-data"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["section"], "A")
        self.assertEqual(len(response.data["students"]), 1)
        self.assertEqual(response.data["students"][0]["crn"], "25BBA001")

    def test_student_cannot_access_student_data_page_api(self):
        self._auth(self.student_token)
        response = self.client.get(reverse("teacher-student-data"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_selected_student_includes_profile_and_attendance_history(self):
        self._auth(self.teacher_token)
        response = self.client.get(reverse("teacher-student-data"), {"section": "A", "crn": "25BBA001"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        selected = response.data["selected_student"]
        self.assertEqual(selected["name"], "Anaya Rao")
        self.assertEqual(selected["username"], "25BBA001")
        self.assertEqual(selected["contact_number"], "9876543210")
        self.assertIn("cannot be shown", selected["password_note"])
        self.assertFalse(selected["trusted_device_bound"])
        self.assertEqual(len(selected["attendance"]), 1)
        self.assertEqual(selected["attendance"][0]["subject"], "AI Training")

    def test_teacher_can_reset_student_password_to_crn(self):
        self.student_a.set_password("ChangedPassword123")
        self.student_a.save(update_fields=["password"])
        self._auth(self.teacher_token)
        response = self.client.post(
            reverse("teacher-student-data"),
            {"crn": "25BBA001", "action": "reset_password_to_crn"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student_a.refresh_from_db()
        self.assertTrue(self.student_a.check_password("25BBA001"))

    def test_teacher_can_reset_student_trusted_device(self):
        profile = self.student_a.student_profile
        profile.trusted_device_hash = "abc123"
        profile.trusted_device_bound_at = timezone.now()
        profile.save(update_fields=["trusted_device_hash", "trusted_device_bound_at"])

        self._auth(self.teacher_token)
        response = self.client.post(
            reverse("teacher-student-data"),
            {"crn": "25BBA001", "action": "reset_trusted_device"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        profile.refresh_from_db()
        self.assertEqual(profile.trusted_device_hash, "")
        self.assertIsNone(profile.trusted_device_bound_at)

    def test_teacher_can_toggle_profile_scan_lock(self):
        self._auth(self.teacher_token)
        response = self.client.post(
            reverse("teacher-student-data"),
            {"action": "toggle_profile_scan_lock", "enabled": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["profile_scan_lock_enabled"])
        self.assertTrue(StudentScanPolicy.current().require_complete_profile)

        response = self.client.get(reverse("teacher-student-data"), {"section": "A"})
        self.assertTrue(response.data["profile_scan_lock_enabled"])
