from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from accounts.models import StudentProfile

User = get_user_model()


class ProfileTest(APITestCase):
    def setUp(self):
        self.student_user = User.objects.create_user(
            username="amanraj", password="pw12345678", role=User.ROLE_STUDENT
        )
        StudentProfile.objects.create(
            user=self.student_user, crn="22030145", course="B.Tech CSE", semester=5, section="A"
        )
        self.token = Token.objects.create(user=self.student_user)

    def test_student_profile_requires_auth(self):
        url = reverse("student-profile")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_profile_returns_data(self):
        url = reverse("student-profile")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["crn"], "22030145")

    def test_authenticated_user_without_profile_gets_404_not_500(self):
        # Covers superusers/teachers/any account with no StudentProfile row hitting
        # this endpoint by mistake (e.g. logging into the app with a Django-admin-only
        # account) — must not crash with an unhandled 500.
        no_profile_user = User.objects.create_user(username="noprofile", password="pw12345678")
        token = Token.objects.create(user=no_profile_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.get(reverse("student-profile"))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
