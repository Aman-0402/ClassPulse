from datetime import datetime, time
from unittest.mock import patch

from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token

from attendance.models import ClassSchedule
from attendance.services import get_current_schedule_slot, get_today_schedule

User = get_user_model()


def _monday_at(hour, minute):
    # 2026-08-10 is a Monday.
    return timezone.make_aware(datetime(2026, 8, 10, hour, minute))


def _monday_date():
    return _monday_at(0, 0).date()


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


class TodayScheduleServiceTest(APITestCase):
    def setUp(self):
        ClassSchedule.objects.all().delete()
        self.monday_a = ClassSchedule.objects.create(
            day_of_week=ClassSchedule.MONDAY, start_time=time(10, 5), end_time=time(10, 55), section="A"
        )
        self.monday_b = ClassSchedule.objects.create(
            day_of_week=ClassSchedule.MONDAY, start_time=time(12, 45), end_time=time(13, 35), section="B"
        )
        ClassSchedule.objects.create(
            day_of_week=ClassSchedule.TUESDAY, start_time=time(10, 5), end_time=time(10, 55), section="D"
        )

    def test_returns_only_todays_slots_in_order(self):
        with patch("attendance.services.timezone.localdate", return_value=_monday_date()):
            slots = list(get_today_schedule())
        self.assertEqual(slots, [self.monday_a, self.monday_b])


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


class TodayScheduleViewTest(APITestCase):
    def setUp(self):
        ClassSchedule.objects.all().delete()
        ClassSchedule.objects.create(
            day_of_week=ClassSchedule.MONDAY,
            start_time=time(10, 5),
            end_time=time(10, 55),
            section="A",
            subject="Training II",
        )
        ClassSchedule.objects.create(
            day_of_week=ClassSchedule.MONDAY,
            start_time=time(12, 45),
            end_time=time(13, 35),
            section="B",
            subject="Training II",
        )
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.student = User.objects.create_user(username="stud", password="pw12345678", role=User.ROLE_STUDENT)

    def test_teacher_sees_all_of_todays_slots(self):
        token = Token.objects.create(user=self.teacher)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        with patch("attendance.services.timezone.localdate", return_value=_monday_date()):
            response = self.client.get(reverse("schedule-today"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["day"], "Monday")
        self.assertEqual(len(response.data["slots"]), 2)
        self.assertEqual(response.data["slots"][0]["section"], "A")
        self.assertEqual(response.data["slots"][1]["section"], "B")

    def test_student_can_also_access(self):
        token = Token.objects.create(user=self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        with patch("attendance.services.timezone.localdate", return_value=_monday_date()):
            response = self.client.get(reverse("schedule-today"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
