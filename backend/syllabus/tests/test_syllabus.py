from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from syllabus.models import SyllabusSession

User = get_user_model()


class SyllabusTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.student = User.objects.create_user(username="s", password="pw12345678", role=User.ROLE_STUDENT)

    def _as(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=user).key}")

    def test_seed_migration_created_48_sessions(self):
        self.assertEqual(SyllabusSession.objects.count(), 48)
        self.assertEqual(SyllabusSession.objects.get(session_number=1).topics, "Introduction to AI, AI in Business, Types of AI")
        self.assertEqual(SyllabusSession.objects.get(session_number=48).topics, "Viva Voce, Future of AI, Programme Wrap-up")

    def test_students_can_view_but_not_manage(self):
        self._as(self.student)
        response = self.client.get(reverse("syllabus-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 48)
        self.assertEqual(response.data[0]["session_number"], 1)
        self.assertEqual(self.client.get(reverse("syllabus-manage-list")).status_code, 403)
        self.assertEqual(
            self.client.post(reverse("syllabus-manage-list"), {"session_number": 49, "topics": "X"}, format="json").status_code,
            403,
        )

    def test_teacher_can_add_edit_delete(self):
        self._as(self.teacher)
        created = self.client.post(
            reverse("syllabus-manage-list"), {"session_number": 49, "topics": "Bonus session"}, format="json"
        )
        self.assertEqual(created.status_code, 201)
        detail = reverse("syllabus-manage-detail", args=[created.data["id"]])
        updated = self.client.patch(detail, {"topics": "Updated bonus session"}, format="json")
        self.assertEqual(updated.data["topics"], "Updated bonus session")
        self.assertEqual(self.client.delete(detail).status_code, 204)
        self.assertEqual(SyllabusSession.objects.count(), 48)

    def test_duplicate_session_number_rejected(self):
        self._as(self.teacher)
        response = self.client.post(
            reverse("syllabus-manage-list"), {"session_number": 1, "topics": "Dup"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_blank_topics_rejected(self):
        self._as(self.teacher)
        response = self.client.post(
            reverse("syllabus-manage-list"), {"session_number": 50, "topics": "   "}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_list_is_ordered_by_session_number(self):
        self._as(self.student)
        numbers = [row["session_number"] for row in self.client.get(reverse("syllabus-list")).data]
        self.assertEqual(numbers, sorted(numbers))
