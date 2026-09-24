from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import StudentProfile
from attendance.models import Attendance, AttendanceSession
from syllabus.models import SyllabusCompletion, SyllabusSession

User = get_user_model()


class SyllabusCompletionTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.teacher).key}")
        self.session = SyllabusSession.objects.create(session_number=500, topics="Intro")
        self.mark_url = reverse("syllabus-mark-completion", args=[self.session.id])

    def test_mark_complete_creates_record(self):
        response = self.client.post(
            self.mark_url, {"section": "a", "date": "2026-09-10", "present_count": 42}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["section"], "A")
        self.assertEqual(response.data["present_count"], 42)
        self.assertEqual(response.data["marked_by_name"], "prof")

    def test_marking_again_updates_not_duplicates(self):
        self.client.post(self.mark_url, {"section": "A", "date": "2026-09-10", "present_count": 40}, format="json")
        self.client.post(self.mark_url, {"section": "A", "date": "2026-09-12", "present_count": 45}, format="json")
        self.assertEqual(SyllabusCompletion.objects.filter(session=self.session, section="A").count(), 1)
        record = SyllabusCompletion.objects.get(session=self.session, section="A")
        self.assertEqual(record.present_count, 45)

    def test_same_session_independent_per_section(self):
        self.client.post(self.mark_url, {"section": "A", "date": "2026-09-10", "present_count": 40}, format="json")
        self.assertEqual(SyllabusCompletion.objects.filter(section="B").count(), 0)
        self.client.post(self.mark_url, {"section": "B", "date": "2026-09-11", "present_count": 38}, format="json")
        self.assertEqual(SyllabusCompletion.objects.filter(session=self.session).count(), 2)

    def test_unmark_deletes_record(self):
        self.client.post(self.mark_url, {"section": "A", "date": "2026-09-10", "present_count": 40}, format="json")
        response = self.client.delete(f"{self.mark_url}?section=A")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(SyllabusCompletion.objects.exists())

    def test_unmark_nonexistent_returns_404(self):
        response = self.client.delete(f"{self.mark_url}?section=A")
        self.assertEqual(response.status_code, 404)

    def test_negative_present_count_rejected(self):
        response = self.client.post(
            self.mark_url, {"section": "A", "date": "2026-09-10", "present_count": -1}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_students_cannot_mark(self):
        student = User.objects.create_user(username="s", password="pw12345678", role=User.ROLE_STUDENT)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=student).key}")
        response = self.client.post(
            self.mark_url, {"section": "A", "date": "2026-09-10", "present_count": 40}, format="json"
        )
        self.assertEqual(response.status_code, 403)


class AttendanceLookupTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.teacher).key}")
        self.url = reverse("syllabus-attendance-lookup")

    def test_returns_present_count_from_closed_session(self):
        session = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI", section="A", date="2026-09-10",
            status=AttendanceSession.STATUS_CLOSED,
        )
        for i in range(3):
            student = User.objects.create_user(username=f"s{i}", password="pw12345678", role=User.ROLE_STUDENT)
            Attendance.objects.create(student=student, session=session)
        response = self.client.get(self.url, {"section": "a", "date": "2026-09-10"})
        self.assertEqual(response.data["present_count"], 3)

    def test_no_session_returns_null(self):
        response = self.client.get(self.url, {"section": "A", "date": "2026-09-10"})
        self.assertIsNone(response.data["present_count"])

    def test_open_session_not_counted(self):
        AttendanceSession.objects.create(teacher=self.teacher, subject="AI", section="A", date="2026-09-10")
        response = self.client.get(self.url, {"section": "A", "date": "2026-09-10"})
        self.assertIsNone(response.data["present_count"])

    def test_missing_params_rejected(self):
        self.assertEqual(self.client.get(self.url, {"section": "A"}).status_code, 400)

    def test_students_cannot_lookup(self):
        student = User.objects.create_user(username="s", password="pw12345678", role=User.ROLE_STUDENT)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=student).key}")
        self.assertEqual(self.client.get(self.url, {"section": "A", "date": "2026-09-10"}).status_code, 403)


class SyllabusListCompletionVisibilityTest(APITestCase):
    def setUp(self):
        self.session = SyllabusSession.objects.create(session_number=500, topics="Intro")
        teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        SyllabusCompletion.objects.create(session=self.session, section="A", date="2026-09-10", present_count=40)
        SyllabusCompletion.objects.create(session=self.session, section="B", date="2026-09-11", present_count=38)

        self.student_a = User.objects.create_user(username="sa", password="pw12345678", role=User.ROLE_STUDENT)
        StudentProfile.objects.create(user=self.student_a, crn="sa", urn="ua", course="BBA", semester=3, section="A")
        self.teacher_token = Token.objects.create(user=teacher).key

    def _my_session(self, response):
        return next(row for row in response.data if row["session_number"] == 500)

    def test_student_sees_only_their_own_section_completion(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.student_a).key}")
        response = self.client.get(reverse("syllabus-list"))
        completions = self._my_session(response)["completions"]
        self.assertEqual(len(completions), 1)
        self.assertEqual(completions[0]["section"], "A")
        self.assertEqual(completions[0]["date"], "2026-09-10")
        self.assertNotIn("present_count", completions[0])

    def test_teacher_sees_every_section_completion(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.teacher_token}")
        response = self.client.get(reverse("syllabus-list"))
        completions = self._my_session(response)["completions"]
        self.assertEqual({c["section"] for c in completions}, {"A", "B"})
