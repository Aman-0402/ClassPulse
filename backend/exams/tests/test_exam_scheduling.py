from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from exams.models import Exam, MCQQuestion, PracticalQuestion

User = get_user_model()


class ExamSchedulingTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.teacher).key}")
        self.url = reverse("exam-list")
        for i in range(5):
            MCQQuestion.objects.create(
                text=f"Q{i}", option_a="a", option_b="b", option_c="c", option_d="d", correct_option="a"
            )
        self.easy = PracticalQuestion.objects.create(text="Easy Q", difficulty="easy")
        self.hard = PracticalQuestion.objects.create(text="Hard Q", difficulty="hard")
        self.now = timezone.now()

    def _payload(self, **overrides):
        data = {
            "title": "Midterm",
            "section": "a",
            "easy_practical": self.easy.id,
            "hard_practical": self.hard.id,
            "start_time": self.now.isoformat(),
            "end_time": (self.now + timezone.timedelta(hours=1)).isoformat(),
        }
        data.update(overrides)
        return data

    def test_create_normalises_section(self):
        response = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["section"], "A")
        self.assertTrue(response.data["is_open"])

    def test_needs_at_least_five_active_mcqs(self):
        MCQQuestion.objects.all().update(is_active=False)
        response = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(response.status_code, 400)

    def test_end_must_be_after_start(self):
        response = self.client.post(
            self.url, self._payload(end_time=(self.now - timezone.timedelta(hours=1)).isoformat()), format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("end_time", response.data)

    def test_easy_practical_must_be_tagged_easy(self):
        response = self.client.post(self.url, self._payload(easy_practical=self.hard.id), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("easy_practical", response.data)

    def test_hard_practical_must_be_tagged_hard(self):
        response = self.client.post(self.url, self._payload(hard_practical=self.easy.id), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("hard_practical", response.data)

    def test_is_open_reflects_window(self):
        future = self.client.post(
            self.url,
            self._payload(
                start_time=(self.now + timezone.timedelta(days=1)).isoformat(),
                end_time=(self.now + timezone.timedelta(days=2)).isoformat(),
            ),
            format="json",
        ).data
        self.assertFalse(future["is_open"])

    def test_manual_forced_open_overrides_window(self):
        created = self.client.post(
            self.url,
            self._payload(
                start_time=(self.now + timezone.timedelta(days=1)).isoformat(),
                end_time=(self.now + timezone.timedelta(days=2)).isoformat(),
            ),
            format="json",
        ).data
        detail = reverse("exam-detail", args=[created["id"]])
        response = self.client.patch(detail, {"manual_status": "forced_open"}, format="json")
        self.assertTrue(response.data["is_open"])

    def test_manual_forced_closed_overrides_window(self):
        created = self.client.post(self.url, self._payload(), format="json").data
        detail = reverse("exam-detail", args=[created["id"]])
        response = self.client.patch(detail, {"manual_status": "forced_closed"}, format="json")
        self.assertFalse(response.data["is_open"])

    def test_section_filter(self):
        self.client.post(self.url, self._payload(section="A"), format="json")
        self.client.post(self.url, self._payload(section="B"), format="json")
        self.assertEqual(len(self.client.get(self.url, {"section": "b"}).data), 1)

    def test_delete(self):
        created = self.client.post(self.url, self._payload(), format="json").data
        detail = reverse("exam-detail", args=[created["id"]])
        self.assertEqual(self.client.delete(detail).status_code, 204)
        self.assertFalse(Exam.objects.exists())

    def test_students_cannot_manage_exams(self):
        student = User.objects.create_user(username="s", password="pw12345678", role=User.ROLE_STUDENT)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=student).key}")
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, self._payload(), format="json").status_code, 403)
