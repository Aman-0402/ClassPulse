from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import StudentProfile, StudentScanPolicy

User = get_user_model()


class ScanProfileFieldsTest(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="25BBA015", password="25BBA015", role=User.ROLE_STUDENT, email="25262101758@bba.local"
        )
        self.profile = StudentProfile.objects.create(
            user=self.student, crn="25BBA015", urn="25262101758", course="BBA", semester=3, section="A"
        )
        token = Token.objects.create(user=self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def _lock(self, enabled):
        policy = StudentScanPolicy.current()
        policy.require_complete_profile = enabled
        policy.save(update_fields=["require_complete_profile"])

    def test_profile_lists_every_missing_field_and_lock_state(self):
        response = self.client.get(reverse("student-profile"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["missing_scan_fields"], ["photo", "email", "contact_number"])
        self.assertFalse(response.data["scan_lock_enabled"])

    def test_lock_state_reflects_policy(self):
        self._lock(True)
        self.assertTrue(self.client.get(reverse("student-profile")).data["scan_lock_enabled"])

    def test_saving_contact_number_clears_it_from_missing(self):
        response = self.client.post(
            reverse("update-contact-number"), {"contact_number": "9876543210"}, format="json"
        )
        self.assertEqual(response.data["missing_scan_fields"], ["photo", "email"])

    def test_saving_a_real_email_clears_it_from_missing(self):
        response = self.client.post(reverse("update-email"), {"email": "me@gmail.com"}, format="json")
        self.assertEqual(response.data["missing_scan_fields"], ["photo", "contact_number"])

    def test_fully_complete_profile_has_nothing_missing(self):
        self.student.email = "me@gmail.com"
        self.student.save(update_fields=["email"])
        self.profile.contact_number = "9876543210"
        self.profile.photo = "student_photos/me.jpg"
        self.profile.save(update_fields=["contact_number", "photo"])
        self.assertEqual(self.client.get(reverse("student-profile")).data["missing_scan_fields"], [])
