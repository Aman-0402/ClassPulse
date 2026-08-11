from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory
from accounts.permissions import IsTeacher, IsStudent

User = get_user_model()


class RolePermissionTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.student = User.objects.create_user(username="stud", password="pw12345678", role=User.ROLE_STUDENT)

    def _request_for(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_is_teacher_allows_teacher(self):
        self.assertTrue(IsTeacher().has_permission(self._request_for(self.teacher), None))

    def test_is_teacher_rejects_student(self):
        self.assertFalse(IsTeacher().has_permission(self._request_for(self.student), None))

    def test_is_student_allows_student(self):
        self.assertTrue(IsStudent().has_permission(self._request_for(self.student), None))

    def test_is_student_rejects_teacher(self):
        self.assertFalse(IsStudent().has_permission(self._request_for(self.teacher), None))
