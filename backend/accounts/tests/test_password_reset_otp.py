from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token

from accounts.models import PasswordResetOTP

User = get_user_model()


class ForgotPasswordTest(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="25BBA015", password="DIVYBBA015", role=User.ROLE_STUDENT
        )

    def test_request_otp_for_real_student_creates_record(self):
        response = self.client.post(reverse("forgot-password"), {"username": "25BBA015"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(PasswordResetOTP.objects.filter(user=self.student).count(), 1)

    def test_unknown_username_returns_same_generic_response_no_otp_created(self):
        response = self.client.post(reverse("forgot-password"), {"username": "nonexistent"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(PasswordResetOTP.objects.count(), 0)

    def test_teacher_username_does_not_create_otp(self):
        # OTP is a student-forgot-password flow specifically.
        User.objects.create_user(username="thinklikeaman", password="x", role=User.ROLE_TEACHER)
        self.client.post(reverse("forgot-password"), {"username": "thinklikeaman"}, format="json")
        self.assertEqual(PasswordResetOTP.objects.count(), 0)

    def test_otp_code_is_six_digits(self):
        self.client.post(reverse("forgot-password"), {"username": "25BBA015"}, format="json")
        otp = PasswordResetOTP.objects.get()
        self.assertEqual(len(otp.code), 6)
        self.assertTrue(otp.code.isdigit())


class ResetPasswordTest(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="25BBA015", password="DIVYBBA015", role=User.ROLE_STUDENT
        )
        self.otp = PasswordResetOTP.objects.create(user=self.student)

    def test_correct_otp_resets_password(self):
        response = self.client.post(
            reverse("reset-password"),
            {"username": "25BBA015", "otp": self.otp.code, "new_password": "BrandNewPass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password("BrandNewPass123"))

    def test_otp_marked_used_after_successful_reset(self):
        self.client.post(
            reverse("reset-password"),
            {"username": "25BBA015", "otp": self.otp.code, "new_password": "BrandNewPass123"},
            format="json",
        )
        self.otp.refresh_from_db()
        self.assertIsNotNone(self.otp.used_at)

    def test_used_otp_cannot_be_reused(self):
        self.client.post(
            reverse("reset-password"),
            {"username": "25BBA015", "otp": self.otp.code, "new_password": "FirstReset123"},
            format="json",
        )
        response = self.client.post(
            reverse("reset-password"),
            {"username": "25BBA015", "otp": self.otp.code, "new_password": "SecondReset123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password("FirstReset123"))

    def test_wrong_otp_rejected(self):
        response = self.client.post(
            reverse("reset-password"),
            {"username": "25BBA015", "otp": "000000", "new_password": "BrandNewPass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password("DIVYBBA015"))

    def test_expired_otp_rejected(self):
        self.otp.expires_at = timezone.now() - timezone.timedelta(minutes=1)
        self.otp.save(update_fields=["expires_at"])
        response = self.client.post(
            reverse("reset-password"),
            {"username": "25BBA015", "otp": self.otp.code, "new_password": "BrandNewPass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_new_password_rejected(self):
        response = self.client.post(
            reverse("reset-password"),
            {"username": "25BBA015", "otp": self.otp.code, "new_password": "123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password("DIVYBBA015"))

    def test_reset_revokes_existing_token(self):
        token = Token.objects.create(user=self.student)
        self.client.post(
            reverse("reset-password"),
            {"username": "25BBA015", "otp": self.otp.code, "new_password": "BrandNewPass123"},
            format="json",
        )
        self.assertFalse(Token.objects.filter(pk=token.pk).exists())
