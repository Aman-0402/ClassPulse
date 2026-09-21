from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from attendance.models import ClassSchedule

User = get_user_model()


class TimetableAdminTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.teacher).key}")
        ClassSchedule.objects.all().delete()  # a data migration seeds the real timetable
        self.url = reverse("timetable-list")

    def _payload(self, **overrides):
        data = {
            "day_of_week": 0,
            "start_time": "10:00",
            "end_time": "10:50",
            "section": "a",
            "subject": "AI Training",
        }
        data.update(overrides)
        return data

    def test_create_normalises_section_and_lists_it(self):
        response = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["section"], "A")
        self.assertEqual(response.data["day_name"], "Monday")
        self.assertEqual(len(self.client.get(self.url).data), 1)

    def test_end_must_be_after_start(self):
        response = self.client.post(self.url, self._payload(end_time="09:00"), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("end_time", response.data)

    def test_overlap_for_same_section_and_day_rejected(self):
        self.client.post(self.url, self._payload(), format="json")
        clash = self.client.post(self.url, self._payload(start_time="10:30", end_time="11:20"), format="json")
        self.assertEqual(clash.status_code, 400)
        self.assertIn("Overlaps", str(clash.data["start_time"]))

    def test_back_to_back_and_other_section_allowed(self):
        self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(
            self.client.post(self.url, self._payload(start_time="10:50", end_time="11:40"), format="json").status_code,
            201,
        )
        self.assertEqual(self.client.post(self.url, self._payload(section="B"), format="json").status_code, 201)

    def test_update_can_keep_own_slot_and_delete_works(self):
        slot = ClassSchedule.objects.create(
            day_of_week=1, start_time="09:00", end_time="09:50", section="A", subject="AI Training"
        )
        detail = reverse("timetable-detail", args=[slot.pk])
        self.assertEqual(self.client.patch(detail, {"subject": "Maths"}, format="json").status_code, 200)
        slot.refresh_from_db()
        self.assertEqual(slot.subject, "Maths")
        self.assertEqual(self.client.delete(detail).status_code, 204)
        self.assertFalse(ClassSchedule.objects.exists())

    def test_section_filter(self):
        self.client.post(self.url, self._payload(section="A"), format="json")
        self.client.post(self.url, self._payload(section="B"), format="json")
        self.assertEqual(len(self.client.get(self.url, {"section": "b"}).data), 1)

    def test_students_cannot_edit_timetable(self):
        student = User.objects.create_user(username="s", password="pw12345678", role=User.ROLE_STUDENT)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=student).key}")
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, self._payload(), format="json").status_code, 403)
