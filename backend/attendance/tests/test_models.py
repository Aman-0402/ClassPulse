from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from attendance.models import AttendanceSession, QRToken, Attendance

User = get_user_model()


class AttendanceModelsTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.student = User.objects.create_user(username="stud", password="pw12345678", role=User.ROLE_STUDENT)
        self.session = AttendanceSession.objects.create(teacher=self.teacher, subject="AI")

    def test_session_defaults_to_active(self):
        self.assertEqual(self.session.status, AttendanceSession.STATUS_ACTIVE)

    def test_qr_token_gets_expiry_on_save(self):
        token = QRToken.objects.create(session=self.session)
        self.assertIsNotNone(token.expires_at)
        self.assertFalse(token.is_expired())

    def test_qr_token_is_expired_after_lifetime(self):
        token = QRToken.objects.create(session=self.session)
        token.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        token.save()
        self.assertTrue(token.is_expired())

    def test_duplicate_attendance_rejected_at_db_level(self):
        Attendance.objects.create(student=self.student, session=self.session)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Attendance.objects.create(student=self.student, session=self.session)
