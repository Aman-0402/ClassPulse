from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

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
