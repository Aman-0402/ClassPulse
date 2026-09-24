import io

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from exams.models import MCQQuestion

User = get_user_model()


def csv_file(content: str, name="questions.csv") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content.encode("utf-8"), content_type="text/csv")


class MCQBulkUploadTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.teacher).key}")
        self.url = reverse("mcq-bulk-upload")

    def test_uploads_all_valid_rows(self):
        content = (
            "text,option_a,option_b,option_c,option_d,correct_option\n"
            "2+2?,3,4,5,6,b\n"
            "Capital of France?,London,Paris,Berlin,Rome,B\n"
        )
        response = self.client.post(self.url, {"file": csv_file(content)}, format="multipart")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["created"], 2)
        self.assertEqual(response.data["errors"], [])
        self.assertEqual(MCQQuestion.objects.count(), 2)
        self.assertEqual(MCQQuestion.objects.first().correct_option, "b")
        self.assertEqual(MCQQuestion.objects.filter(created_by=self.teacher).count(), 2)

    def test_column_order_and_case_do_not_matter(self):
        content = "Correct_Option,Text,Option_A,Option_B,Option_C,Option_D\nc,Q1,a,b,c,d\n"
        response = self.client.post(self.url, {"file": csv_file(content)}, format="multipart")
        self.assertEqual(response.data["created"], 1)

    def test_bad_rows_reported_good_rows_still_created(self):
        content = (
            "text,option_a,option_b,option_c,option_d,correct_option\n"
            "Good one,a,b,c,d,a\n"
            "Bad option,a,b,c,d,z\n"
            ",a,b,c,d,a\n"
        )
        response = self.client.post(self.url, {"file": csv_file(content)}, format="multipart")
        self.assertEqual(response.data["created"], 1)
        self.assertEqual(len(response.data["errors"]), 2)
        self.assertIn("Row 3", response.data["errors"][0])
        self.assertIn("Row 4", response.data["errors"][1])

    def test_blank_lines_skipped_without_error(self):
        content = "text,option_a,option_b,option_c,option_d,correct_option\nQ1,a,b,c,d,a\n\n\n"
        response = self.client.post(self.url, {"file": csv_file(content)}, format="multipart")
        self.assertEqual(response.data["created"], 1)
        self.assertEqual(response.data["errors"], [])

    def test_missing_required_column_rejected(self):
        content = "text,option_a,option_b,option_c\nQ1,a,b,c\n"
        response = self.client.post(self.url, {"file": csv_file(content)}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertIn("option_d", response.data["detail"])

    def test_no_file_rejected(self):
        response = self.client.post(self.url, {}, format="multipart")
        self.assertEqual(response.status_code, 400)

    def test_students_cannot_bulk_upload(self):
        student = User.objects.create_user(username="s", password="pw12345678", role=User.ROLE_STUDENT)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=student).key}")
        content = "text,option_a,option_b,option_c,option_d,correct_option\nQ1,a,b,c,d,a\n"
        response = self.client.post(self.url, {"file": csv_file(content)}, format="multipart")
        self.assertEqual(response.status_code, 403)
