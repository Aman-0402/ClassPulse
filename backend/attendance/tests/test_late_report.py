from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import StudentProfile
from attendance.models import Attendance, AttendanceSession

User = get_user_model()


class LateReportTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        token = Token.objects.create(user=self.teacher)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.start = timezone.now() - timezone.timedelta(hours=2)
        self.session = self._session("A")

    def _session(self, section):
        return AttendanceSession.objects.create(
            teacher=self.teacher,
            subject="AI",
            section=section,
            start_time=self.start,
            status=AttendanceSession.STATUS_CLOSED,
        )

    def _student(self, crn, section, minutes_after, manual=False, session=None):
        user = User.objects.create_user(username=crn, password=crn, role=User.ROLE_STUDENT, first_name=crn)
        StudentProfile.objects.create(user=user, crn=crn, urn=crn + "9", course="BBA", semester=3, section=section)
        record = Attendance.objects.create(
            student=user,
            session=session or self.session,
            device_info="manual override by teacher" if manual else "phone",
        )
        Attendance.objects.filter(pk=record.pk).update(
            marked_at=self.start + timezone.timedelta(minutes=minutes_after)
        )
        return user

    def _get(self, **params):
        return self.client.get(reverse("late-report"), params)

    def test_lists_only_students_late_by_the_threshold(self):
        self._student("S1", "A", 2)
        self._student("S2", "A", 10)
        self._student("S3", "A", 16)
        response = self._get(min_minutes=10)
        self.assertEqual([s["crn"] for s in response.data["students"]], ["S3", "S2"])
        self.assertEqual(response.data["total_scans"], 3)
        self.assertEqual(response.data["late_scans"], 2)
        self.assertEqual(response.data["students"][0]["max_late"], 16.0)

    def test_fifteen_minute_threshold(self):
        self._student("S2", "A", 10)
        self._student("S3", "A", 16)
        self.assertEqual([s["crn"] for s in self._get(min_minutes=15).data["students"]], ["S3"])

    def test_zero_lists_every_scan_time(self):
        self._student("S1", "A", 1)
        self.assertEqual(len(self._get(min_minutes=0).data["students"]), 1)

    def test_manual_attendance_is_not_counted_as_late(self):
        self._student("S1", "A", 40, manual=True)
        self.assertEqual(self._get(min_minutes=10).data["students"], [])

    def test_section_filter_and_section_summary(self):
        self._student("S1", "A", 20)
        self._student("S9", "B", 30, session=self._session("B"))
        everyone = self._get(min_minutes=10).data
        self.assertEqual([b["section"] for b in everyone["sections"]], ["A", "B"])
        only_b = self._get(min_minutes=10, section="B").data
        self.assertEqual([s["crn"] for s in only_b["students"]], ["S9"])

    def test_students_cannot_view_report(self):
        student = User.objects.create_user(username="x", password="pw12345678", role=User.ROLE_STUDENT)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=student).key}")
        self.assertEqual(self._get().status_code, 403)

    def test_bad_params_rejected(self):
        self.assertEqual(self._get(min_minutes="abc").status_code, 400)
        self.assertEqual(self._get(min_minutes=-1).status_code, 400)
