from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import StudentProfile
from attendance.models import NotAttendingMark

User = get_user_model()


class NotAttendingReportTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.teacher).key}")
        self.url = reverse("not-attending-report")

    def _student(self, crn, section, name=""):
        user = User.objects.create_user(username=crn, password=crn, role=User.ROLE_STUDENT, first_name=name or crn)
        StudentProfile.objects.create(user=user, crn=crn, urn=crn + "9", course="BBA", semester=3, section=section)
        return user

    def test_lists_students_with_marks_grouped_by_student(self):
        s1 = self._student("S1", "A")
        s2 = self._student("S2", "A")
        NotAttendingMark.objects.create(student=s1, section="A", date="2026-09-01")
        NotAttendingMark.objects.create(student=s1, section="A", date="2026-09-08")
        NotAttendingMark.objects.create(student=s2, section="A", date="2026-09-03")

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_marks"], 3)
        by_crn = {s["crn"]: s for s in response.data["students"]}
        self.assertEqual(by_crn["S1"]["count"], 2)
        self.assertEqual(by_crn["S1"]["dates"], ["2026-09-08", "2026-09-01"])
        self.assertEqual(by_crn["S2"]["count"], 1)

    def test_sorted_by_count_descending(self):
        s1 = self._student("S1", "A")
        s2 = self._student("S2", "A")
        NotAttendingMark.objects.create(student=s2, section="A", date="2026-09-01")
        NotAttendingMark.objects.create(student=s1, section="A", date="2026-09-01")
        NotAttendingMark.objects.create(student=s1, section="A", date="2026-09-08")

        response = self.client.get(self.url)
        self.assertEqual([s["crn"] for s in response.data["students"]], ["S1", "S2"])

    def test_section_filter(self):
        s1 = self._student("S1", "A")
        s2 = self._student("S2", "B")
        NotAttendingMark.objects.create(student=s1, section="A", date="2026-09-01")
        NotAttendingMark.objects.create(student=s2, section="B", date="2026-09-01")

        response = self.client.get(self.url, {"section": "B"})
        self.assertEqual([s["crn"] for s in response.data["students"]], ["S2"])
        self.assertEqual([b["section"] for b in response.data["sections"]], ["B"])

    def test_date_range_filter(self):
        s1 = self._student("S1", "A")
        NotAttendingMark.objects.create(student=s1, section="A", date="2026-09-01")
        NotAttendingMark.objects.create(student=s1, section="A", date="2026-09-20")

        response = self.client.get(self.url, {"date_from": "2026-09-10"})
        self.assertEqual(response.data["students"][0]["count"], 1)
        self.assertEqual(response.data["students"][0]["dates"], ["2026-09-20"])

    def test_empty_when_no_marks(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data["students"], [])
        self.assertEqual(response.data["total_marks"], 0)

    def test_bad_date_rejected(self):
        response = self.client.get(self.url, {"date_from": "not-a-date"})
        self.assertEqual(response.status_code, 400)

    def test_students_cannot_view_report(self):
        student = self._student("S1", "A")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=student).key}")
        self.assertEqual(self.client.get(self.url).status_code, 403)
