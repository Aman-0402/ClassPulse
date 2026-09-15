from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import StudentProfile

User = get_user_model()


class LoginTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="amanraj", password="StrongPass123", role=User.ROLE_STUDENT
        )

    def test_login_returns_token_and_role(self):
        url = reverse("login")
        response = self.client.post(
            url, {"username": "amanraj", "password": "StrongPass123"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["role"], "student")

    def test_login_wrong_password_rejected(self):
        url = reverse("login")
        response = self.client.post(
            url, {"username": "amanraj", "password": "wrong"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_login_does_not_bind_phone(self):
        StudentProfile.objects.create(user=self.user, crn="25BBA001", urn="1", course="BBA", semester=3, section="A")
        response = self.client.post(
            reverse("login"),
            {"username": "amanraj", "password": "StrongPass123"},
            format="json",
            HTTP_X_CLASSPULSE_DEVICE_ID="phone-a",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.student_profile.refresh_from_db()
        self.assertEqual(self.user.student_profile.trusted_device_hash, "")

    def test_same_phone_can_login_as_second_student(self):
        StudentProfile.objects.create(user=self.user, crn="25BBA001", urn="1", course="BBA", semester=3, section="A")
        other = User.objects.create_user(username="friend", password="StrongPass123", role=User.ROLE_STUDENT)
        StudentProfile.objects.create(user=other, crn="25BBA002", urn="2", course="BBA", semester=3, section="A")

        self.client.post(
            reverse("login"),
            {"username": "amanraj", "password": "StrongPass123"},
            format="json",
            HTTP_X_CLASSPULSE_DEVICE_ID="phone-a",
        )
        response = self.client.post(
            reverse("login"),
            {"username": "friend", "password": "StrongPass123"},
            format="json",
            HTTP_X_CLASSPULSE_DEVICE_ID="phone-a",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

    def test_bound_student_can_login_from_second_phone(self):
        StudentProfile.objects.create(user=self.user, crn="25BBA001", urn="1", course="BBA", semester=3, section="A")
        self.client.post(
            reverse("login"),
            {"username": "amanraj", "password": "StrongPass123"},
            format="json",
            HTTP_X_CLASSPULSE_DEVICE_ID="phone-a",
        )
        response = self.client.post(
            reverse("login"),
            {"username": "amanraj", "password": "StrongPass123"},
            format="json",
            HTTP_X_CLASSPULSE_DEVICE_ID="phone-b",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
