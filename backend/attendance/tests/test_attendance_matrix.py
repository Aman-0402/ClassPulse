from django.contrib.auth import get_user_model
from django.test import TestCase
from attendance.models import AttendanceSession, Attendance
from attendance.services import build_attendance_matrix, get_closed_sessions

User = get_user_model()


class AttendanceMatrixTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.s1 = User.objects.create_user(
            username="stud1", password="pw12345678", role=User.ROLE_STUDENT, first_name="Aman Raj"
        )
        self.s2 = User.objects.create_user(
            username="stud2", password="pw12345678", role=User.ROLE_STUDENT, first_name="Priya Singh"
        )
        from accounts.models import StudentProfile

        StudentProfile.objects.create(user=self.s1, crn="101", course="CSE", semester=5, section="A")
        StudentProfile.objects.create(user=self.s2, crn="102", course="CSE", semester=5, section="A")

        self.closed1 = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI", status=AttendanceSession.STATUS_CLOSED
        )
        self.closed2 = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI", status=AttendanceSession.STATUS_CLOSED
        )
        self.active = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI", status=AttendanceSession.STATUS_ACTIVE
        )

        Attendance.objects.create(student=self.s1, session=self.closed1)
        Attendance.objects.create(student=self.s1, session=self.closed2)
        Attendance.objects.create(student=self.s2, session=self.closed1)
        # s2 absent from closed2; neither has a record for the still-active session

    def test_get_closed_sessions_excludes_active(self):
        sessions = list(get_closed_sessions())
        self.assertEqual(len(sessions), 2)
        self.assertNotIn(self.active, sessions)

    def test_matrix_computes_correct_totals(self):
        sessions, rows = build_attendance_matrix()
        self.assertEqual(len(sessions), 2)
        self.assertEqual(len(rows), 2)

        by_crn = {r["crn"]: r for r in rows}
        self.assertEqual(by_crn["101"]["present_count"], 2)
        self.assertEqual(by_crn["101"]["total"], 2)
        self.assertEqual(by_crn["101"]["percentage"], 100.0)

        self.assertEqual(by_crn["102"]["present_count"], 1)
        self.assertEqual(by_crn["102"]["total"], 2)
        self.assertEqual(by_crn["102"]["percentage"], 50.0)

    def test_matrix_presents_dict_keyed_by_session_id(self):
        _, rows = build_attendance_matrix()
        row = next(r for r in rows if r["crn"] == "102")
        self.assertTrue(row["presents"][self.closed1.id])
        self.assertFalse(row["presents"][self.closed2.id])


class MergedDoublePeriodMatrixTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.student = User.objects.create_user(
            username="stud1", password="pw12345678", role=User.ROLE_STUDENT, first_name="Aman Raj"
        )
        from accounts.models import StudentProfile

        StudentProfile.objects.create(user=self.student, crn="101", course="CSE", semester=5, section="A")

        self.merged_session = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI", status=AttendanceSession.STATUS_CLOSED, periods=2
        )
        self.single_session = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI", status=AttendanceSession.STATUS_CLOSED, periods=1
        )
        # Present for the merged (double) session, absent from the single one.
        Attendance.objects.create(student=self.student, session=self.merged_session)

    def test_merged_session_counts_double_towards_total_and_present(self):
        sessions, rows = build_attendance_matrix()
        row = rows[0]
        # total = 2 (merged) + 1 (single) = 3; present = 2 (merged, attended) + 0 = 2
        self.assertEqual(row["total"], 3)
        self.assertEqual(row["present_count"], 2)
