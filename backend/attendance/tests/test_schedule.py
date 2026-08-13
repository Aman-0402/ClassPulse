from datetime import datetime, time
from unittest.mock import patch

from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token

from attendance.models import ClassSchedule
from attendance.services import get_current_schedule_slot

User = get_user_model()


def _monday_at(hour, minute):
    # 2026-08-10 is a Monday.
    return timezone.make_aware(datetime(2026, 8, 10, hour, minute))


class CurrentScheduleSlotTest(APITestCase):
    def setUp(self):
        ClassSchedule.objects.all().delete()
        self.slot = ClassSchedule.objects.create(
            day_of_week=ClassSchedule.MONDAY,
            start_time=time(10, 5),
            end_time=time(10, 55),
            section="A",
        )

    def test_returns_slot_covering_current_time(self):
        with patch("attendance.services.timezone.localtime", return_value=_monday_at(10, 30)):
            slot = get_current_schedule_slot()
        self.assertEqual(slot, self.slot)

    def test_returns_none_outside_any_slot(self):
        with patch("attendance.services.timezone.localtime", return_value=_monday_at(9, 0)):
            slot = get_current_schedule_slot()
        self.assertIsNone(slot)

    def test_end_time_is_exclusive(self):
        with patch("attendance.services.timezone.localtime", return_value=_monday_at(10, 55)):
            slot = get_current_schedule_slot()
        self.assertIsNone(slot)


class CurrentScheduleViewTest(APITestCase):
    def setUp(self):
        ClassSchedule.objects.all().delete()
        ClassSchedule.objects.create(
            day_of_week=ClassSchedule.MONDAY,
            start_time=time(10, 5),
            end_time=time(10, 55),
            section="A",
            subject="Training II",
        )
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.token = Token.objects.create(user=self.teacher)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_matched_slot_returns_subject_and_section(self):
        with patch("attendance.services.timezone.localtime", return_value=_monday_at(10, 30)):
            response = self.client.get(reverse("schedule-current"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["matched"])
        self.assertEqual(response.data["subject"], "Training II")
        self.assertEqual(response.data["section"], "A")

    def test_no_slot_returns_matched_false(self):
        with patch("attendance.services.timezone.localtime", return_value=_monday_at(9, 0)):
            response = self.client.get(reverse("schedule-current"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"matched": False})

    def test_student_cannot_access(self):
        student = User.objects.create_user(username="stud", password="pw12345678", role=User.ROLE_STUDENT)
        student_token = Token.objects.create(user=student)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {student_token.key}")
        response = self.client.get(reverse("schedule-current"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
