from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from exams.models import MCQQuestion, PracticalQuestion

User = get_user_model()


class MCQBankTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.teacher).key}")
        self.url = reverse("mcq-list")

    def _payload(self, **overrides):
        data = {
            "text": "What is 2 + 2?",
            "option_a": "3",
            "option_b": "4",
            "option_c": "5",
            "option_d": "22",
            "correct_option": "b",
        }
        data.update(overrides)
        return data

    def test_create_records_author(self):
        response = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(MCQQuestion.objects.get().is_active)
        self.assertEqual(MCQQuestion.objects.get().created_by, self.teacher)

    def test_blank_option_rejected(self):
        response = self.client.post(self.url, self._payload(option_c="  "), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("option_c", response.data)

    def test_active_filter(self):
        self.client.post(self.url, self._payload(), format="json")
        inactive = self.client.post(self.url, self._payload(), format="json").data
        self.client.patch(reverse("mcq-detail", args=[inactive["id"]]), {"is_active": False}, format="json")
        self.assertEqual(len(self.client.get(self.url, {"active": "true"}).data), 1)
        self.assertEqual(len(self.client.get(self.url, {"active": "false"}).data), 1)
        self.assertEqual(len(self.client.get(self.url).data), 2)

    def test_delete(self):
        created = self.client.post(self.url, self._payload(), format="json").data
        self.assertEqual(self.client.delete(reverse("mcq-detail", args=[created["id"]])).status_code, 204)
        self.assertFalse(MCQQuestion.objects.exists())

    def test_students_cannot_manage_bank(self):
        student = User.objects.create_user(username="s", password="pw12345678", role=User.ROLE_STUDENT)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=student).key}")
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, self._payload(), format="json").status_code, 403)


class PracticalBankTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.teacher).key}")
        self.url = reverse("practical-list")

    def test_create_easy_and_hard(self):
        self.client.post(self.url, {"text": "Write a SQL query.", "difficulty": "easy"}, format="json")
        self.client.post(self.url, {"text": "Design a schema.", "difficulty": "hard"}, format="json")
        self.assertEqual(PracticalQuestion.objects.count(), 2)
        self.assertEqual(len(self.client.get(self.url, {"difficulty": "hard"}).data), 1)

    def test_blank_text_rejected(self):
        response = self.client.post(self.url, {"text": "  ", "difficulty": "easy"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_invalid_difficulty_rejected(self):
        response = self.client.post(self.url, {"text": "Q", "difficulty": "medium"}, format="json")
        self.assertEqual(response.status_code, 400)
