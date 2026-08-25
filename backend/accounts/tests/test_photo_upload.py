from io import BytesIO

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from accounts.models import StudentProfile

User = get_user_model()


def make_image(width, height, size_bytes_padding=0, fmt="PNG"):
    buffer = BytesIO()
    Image.new("RGB", (width, height), color="blue").save(buffer, format=fmt)
    content = buffer.getvalue() + (b"\x00" * size_bytes_padding)
    return SimpleUploadedFile(f"photo.{fmt.lower()}", content, content_type=f"image/{fmt.lower()}")


class ProfilePhotoUploadTest(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(username="25BBA015", password="pw12345678", role=User.ROLE_STUDENT)
        self.profile = StudentProfile.objects.create(
            user=self.student, crn="25BBA015", urn="25262101758", course="BBA", semester=3, section="A"
        )
        self.token = Token.objects.create(user=self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_square_photo_under_1mb_accepted(self):
        photo = make_image(200, 200)
        response = self.client.post(reverse("profile-photo"), {"photo": photo}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertTrue(bool(self.profile.photo))
        self.assertIsNotNone(response.data["photo"])

    def test_non_square_photo_rejected(self):
        photo = make_image(200, 100)
        response = self.client.post(reverse("profile-photo"), {"photo": photo}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.profile.refresh_from_db()
        self.assertFalse(bool(self.profile.photo))

    def test_photo_over_1mb_rejected(self):
        # A 300x300 PNG is tiny on its own; pad it past 1MB to exercise the size check
        # without needing a genuinely huge (and slow-to-generate) real image.
        photo = make_image(300, 300, size_bytes_padding=1024 * 1024)
        response = self.client.post(reverse("profile-photo"), {"photo": photo}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_teacher_cannot_upload(self):
        teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        token = Token.objects.create(user=teacher)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        photo = make_image(200, 200)
        response = self.client.post(reverse("profile-photo"), {"photo": photo}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_rejected(self):
        self.client.credentials()
        photo = make_image(200, 200)
        response = self.client.post(reverse("profile-photo"), {"photo": photo}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
