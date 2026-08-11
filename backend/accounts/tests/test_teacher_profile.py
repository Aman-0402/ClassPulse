from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token

User = get_user_model()


class TeacherProfileTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="profsharma", password="pw12345678",
            role=User.ROLE_TEACHER, first_name="Sharma", email="sharma@example.com",
        )
        self.token = Token.objects.create(user=self.teacher)

    def test_teacher_profile_requires_auth(self):
        response = self.client.get(reverse("teacher-profile"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_teacher_profile_returns_data(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        response = self.client.get(reverse("teacher-profile"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "sharma@example.com")
