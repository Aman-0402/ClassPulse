from django.test import TestCase
from django.contrib.auth import get_user_model
from attendance.models import AttendanceSession, ActivityLog

User = get_user_model()


class ActivityLogModelTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.student = User.objects.create_user(username="stud", password="pw12345678", role=User.ROLE_STUDENT)
        self.session = AttendanceSession.objects.create(teacher=self.teacher, subject="AI")

    def test_can_create_log_with_session(self):
        log = ActivityLog.objects.create(
            student=self.student,
            session=self.session,
            activity_type=ActivityLog.TYPE_DUPLICATE,
            ip_address="127.0.0.1",
            device_info="pytest-agent",
        )
        self.assertEqual(log.activity_type, "duplicate")

    def test_session_is_nullable(self):
        log = ActivityLog.objects.create(
            student=self.student,
            session=None,
            activity_type=ActivityLog.TYPE_INVALID_TOKEN,
        )
        self.assertIsNone(log.session)

    def test_default_ordering_is_newest_first(self):
        first = ActivityLog.objects.create(student=self.student, activity_type=ActivityLog.TYPE_SUCCESS)
        second = ActivityLog.objects.create(student=self.student, activity_type=ActivityLog.TYPE_SUCCESS)
        logs = list(ActivityLog.objects.all())
        self.assertEqual(logs, [second, first])
