from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class UserModelTest(TestCase):
    def test_default_role_is_student(self):
        user = User.objects.create_user(username="aman", password="pw12345")
        self.assertEqual(user.role, "student")

    def test_can_create_teacher(self):
        user = User.objects.create_user(username="prof", password="pw12345", role="teacher")
        self.assertEqual(user.role, "teacher")

    def test_role_choices_reject_invalid_value_on_full_clean(self):
        user = User(username="bad", role="admin")
        with self.assertRaises(Exception):
            user.full_clean()
