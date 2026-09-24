from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import StudentProfile
from tasks.models import Task

User = get_user_model()


class TeacherTaskTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.teacher).key}")
        self.url = reverse("teacher-task-list")

    def _payload(self, **overrides):
        data = {"title": "Read chapter 3", "description": "Pages 40-55", "section": "a", "due_date": "2026-10-01"}
        data.update(overrides)
        return data

    def test_create_normalises_section_and_records_author(self):
        response = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["section"], "A")
        self.assertEqual(response.data["created_by_name"], "prof")

    def test_title_required(self):
        response = self.client.post(self.url, self._payload(title="   "), format="json")
        self.assertEqual(response.status_code, 400)

    def test_list_can_filter_by_section(self):
        self.client.post(self.url, self._payload(section="A"), format="json")
        self.client.post(self.url, self._payload(section="B"), format="json")
        self.assertEqual(len(self.client.get(self.url).data), 2)
        self.assertEqual(len(self.client.get(self.url, {"section": "b"}).data), 1)

    def test_update_and_delete(self):
        created = self.client.post(self.url, self._payload(), format="json").data
        detail = reverse("teacher-task-detail", args=[created["id"]])
        response = self.client.patch(detail, {"title": "Read chapter 4"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Read chapter 4")
        self.assertEqual(self.client.delete(detail).status_code, 204)
        self.assertFalse(Task.objects.exists())

    def test_students_cannot_manage_tasks(self):
        student = User.objects.create_user(username="s", password="pw12345678", role=User.ROLE_STUDENT)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=student).key}")
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, self._payload(), format="json").status_code, 403)


class StudentTaskTest(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(username="s1", password="pw12345678", role=User.ROLE_STUDENT)
        StudentProfile.objects.create(user=self.student, crn="s1", urn="u1", course="BBA", semester=3, section="A")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.student).key}")
        self.url = reverse("student-task-list")

    def test_student_sees_only_their_section(self):
        Task.objects.create(title="For A", section="A")
        Task.objects.create(title="For B", section="B")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([t["title"] for t in response.data], ["For A"])

    def test_student_without_section_gets_clear_error(self):
        other = User.objects.create_user(username="s2", password="pw12345678", role=User.ROLE_STUDENT)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=other).key}")
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_teacher_cannot_use_student_endpoint(self):
        teacher = User.objects.create_user(username="t", password="pw12345678", role=User.ROLE_TEACHER)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=teacher).key}")
        self.assertEqual(self.client.get(self.url).status_code, 403)
