from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from accounts.models import StudentProfile

User = get_user_model()


class UpdateContactNumberTest(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="25BBA015", password="pw12345678", role=User.ROLE_STUDENT
        )
        StudentProfile.objects.create(
            user=self.student, crn="25BBA015", urn="25262101758", course="BBA", semester=3, section="A"
        )
        self.token = Token.objects.create(user=self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_student_can_set_contact_number(self):
        response = self.client.post(
            reverse("update-contact-number"), {"contact_number": "9876543210"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["contact_number"], "9876543210")

    def test_contact_number_with_country_code_accepted(self):
        response = self.client.post(
            reverse("update-contact-number"), {"contact_number": "+919876543210"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_numeric_contact_number_rejected(self):
        response = self.client.post(
            reverse("update-contact-number"), {"contact_number": "not-a-number"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_too_short_contact_number_rejected(self):
        response = self.client.post(reverse("update-contact-number"), {"contact_number": "12345"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_teacher_cannot_use_student_endpoint(self):
        teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        token = Token.objects.create(user=teacher)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.post(
            reverse("update-contact-number"), {"contact_number": "9876543210"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_rejected(self):
        self.client.credentials()
        response = self.client.post(
            reverse("update-contact-number"), {"contact_number": "9876543210"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
