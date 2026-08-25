from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from accounts.models import StudentProfile

User = get_user_model()


class UpdateEmailTest(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="25BBA015", password="pw12345678", role=User.ROLE_STUDENT, email="25262101758@bba.local"
        )
        StudentProfile.objects.create(
            user=self.student, crn="25BBA015", urn="25262101758", course="BBA", semester=3, section="A"
        )
        self.token = Token.objects.create(user=self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_student_can_update_own_email(self):
        response = self.client.post(reverse("update-email"), {"email": "real.email@gmail.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "real.email@gmail.com")
        self.student.refresh_from_db()
        self.assertEqual(self.student.email, "real.email@gmail.com")

    def test_invalid_email_rejected(self):
        response = self.client.post(reverse("update-email"), {"email": "not-an-email"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.student.refresh_from_db()
        self.assertEqual(self.student.email, "25262101758@bba.local")

    def test_unauthenticated_rejected(self):
        self.client.credentials()
        response = self.client.post(reverse("update-email"), {"email": "x@y.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TeacherUpdateEmailTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="prof", password="pw12345678", role=User.ROLE_TEACHER, email="admin@classpulse.local"
        )
        self.token = Token.objects.create(user=self.teacher)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_teacher_can_update_own_email(self):
        response = self.client.post(reverse("teacher-update-email"), {"email": "prof.real@gmail.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "prof.real@gmail.com")
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.email, "prof.real@gmail.com")

    def test_invalid_email_rejected(self):
        response = self.client.post(reverse("teacher-update-email"), {"email": "not-an-email"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_rejected(self):
        self.client.credentials()
        response = self.client.post(reverse("teacher-update-email"), {"email": "x@y.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
