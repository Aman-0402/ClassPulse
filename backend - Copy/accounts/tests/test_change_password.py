from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token

User = get_user_model()


class ChangePasswordTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="25BBA015", password="DIVYBBA015", role=User.ROLE_STUDENT
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_change_password_with_correct_old_password(self):
        response = self.client.post(
            reverse("change-password"),
            {"old_password": "DIVYBBA015", "new_password": "MyNewSecret123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("MyNewSecret123"))

    def test_wrong_old_password_rejected(self):
        response = self.client.post(
            reverse("change-password"),
            {"old_password": "wrong", "new_password": "MyNewSecret123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("DIVYBBA015"))

    def test_weak_new_password_rejected(self):
        response = self.client.post(
            reverse("change-password"),
            {"old_password": "DIVYBBA015", "new_password": "123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_changing_password_rotates_token(self):
        old_key = self.token.key
        response = self.client.post(
            reverse("change-password"),
            {"old_password": "DIVYBBA015", "new_password": "MyNewSecret123"},
            format="json",
        )
        new_key = response.data["token"]
        self.assertNotEqual(old_key, new_key)
        self.assertEqual(Token.objects.filter(user=self.user).count(), 1)

    def test_unauthenticated_request_rejected(self):
        self.client.credentials()
        response = self.client.post(
            reverse("change-password"),
            {"old_password": "DIVYBBA015", "new_password": "MyNewSecret123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LogoutTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="25BBA015", password="DIVYBBA015", role=User.ROLE_STUDENT
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_logout_revokes_token(self):
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_token_unusable_after_logout(self):
        self.client.post(reverse("logout"))
        response = self.client.get(reverse("student-profile"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
