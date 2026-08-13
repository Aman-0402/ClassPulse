from datetime import datetime, time
from unittest.mock import patch

from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token

from attendance.models import AttendanceSession, ClassSchedule
from attendance.services import get_current_schedule_slot, get_today_schedule, merge_consecutive_slots

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


class MergeConsecutiveSlotsTest(APITestCase):
    def setUp(self):
        ClassSchedule.objects.all().delete()

    def _slot(self, start, end, section, subject="Training II"):
        return ClassSchedule.objects.create(
            day_of_week=ClassSchedule.MONDAY, start_time=start, end_time=end, section=section, subject=subject
        )

    def test_back_to_back_same_section_merges_into_one_block(self):
        first = self._slot(time(10, 5), time(10, 55), "D")
        second = self._slot(time(11, 5), time(11, 55), "D")
        merged = merge_consecutive_slots([first, second])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["start_time"], time(10, 5))
        self.assertEqual(merged[0]["end_time"], time(11, 55))
        self.assertEqual(merged[0]["section"], "D")

    def test_short_break_between_periods_still_merges(self):
        # Real timetable leaves a 10-minute break (10:55 -> 11:05) between periods
        # of the same double-length class — still one continuous session.
        first = self._slot(time(10, 5), time(10, 55), "D")
        second = self._slot(time(11, 5), time(11, 55), "D")
        merged = merge_consecutive_slots([first, second])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["start_time"], time(10, 5))
        self.assertEqual(merged[0]["end_time"], time(11, 55))

    def test_different_section_between_same_section_slots_stops_merge(self):
        first = self._slot(time(10, 5), time(10, 55), "D")
        middle = self._slot(time(11, 5), time(11, 55), "E")
        last = self._slot(time(12, 5), time(12, 55), "D")
        merged = merge_consecutive_slots([first, middle, last])
        self.assertEqual([m["section"] for m in merged], ["D", "E", "D"])

    def test_different_section_does_not_merge(self):
        first = self._slot(time(10, 5), time(10, 55), "D")
        second = self._slot(time(10, 55), time(11, 45), "E")
        merged = merge_consecutive_slots([first, second])
        self.assertEqual(len(merged), 2)

    def test_full_thursday_schedule_merges_into_three_double_periods(self):
        slots = [
            self._slot(time(10, 5), time(10, 55), "D"),
            self._slot(time(11, 5), time(11, 55), "D"),
            self._slot(time(12, 45), time(13, 35), "E"),
            self._slot(time(13, 35), time(14, 25), "E"),
            self._slot(time(14, 35), time(15, 25), "F"),
            self._slot(time(15, 25), time(16, 15), "F"),
        ]
        merged = merge_consecutive_slots(slots)
        self.assertEqual([m["section"] for m in merged], ["D", "E", "F"])
        self.assertEqual(merged[0]["start_time"], time(10, 5))
        self.assertEqual(merged[0]["end_time"], time(11, 55))


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


class TodayScheduleSessionLinkingTest(APITestCase):
    def setUp(self):
        ClassSchedule.objects.all().delete()
        AttendanceSession.objects.all().delete()
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
        token = Token.objects.create(user=self.teacher)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def _get_today(self):
        with patch("attendance.services.timezone.localdate", return_value=_monday_date()):
            return self.client.get(reverse("schedule-today"))

    def test_slot_without_a_session_has_no_session_id(self):
        response = self._get_today()
        section_a = next(s for s in response.data["slots"] if s["section"] == "A")
        self.assertIsNone(section_a["session_id"])
        self.assertIsNone(section_a["session_status"])

    def test_slot_with_a_started_session_links_to_it(self):
        session = AttendanceSession.objects.create(
            teacher=self.teacher, subject="Training II", section="A", date=_monday_date()
        )
        response = self._get_today()
        section_a = next(s for s in response.data["slots"] if s["section"] == "A")
        self.assertEqual(section_a["session_id"], session.id)
        self.assertEqual(section_a["session_status"], AttendanceSession.STATUS_ACTIVE)

    def test_another_teachers_session_does_not_link(self):
        other_teacher = User.objects.create_user(username="prof2", password="pw12345678", role=User.ROLE_TEACHER)
        AttendanceSession.objects.create(
            teacher=other_teacher, subject="Training II", section="A", date=_monday_date()
        )
        response = self._get_today()
        section_a = next(s for s in response.data["slots"] if s["section"] == "A")
        self.assertIsNone(section_a["session_id"])
