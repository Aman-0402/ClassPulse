# Phase 5 — Reports & Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A student can see their attendance history and running percentage. A teacher can see overall/per-student analytics and a below-threshold list, and export the full attendance matrix as CSV, Excel, or PDF.

**Architecture:** ClassPulse v1 is scoped to a single subject/class (doc.md §4, Agent.md's "Out of Scope" section) — there's no course/enrollment model, so "all sessions" and "all students" are unambiguous, system-wide sets. A single shared function, `attendance/services.py::build_attendance_matrix()`, computes the sessions × students × present/absent grid once; analytics and all three export formats (CSV/Excel/PDF) call it rather than each re-deriving the same data differently. Only **closed** sessions count toward totals/percentages — an in-progress session shouldn't retroactively mark a student "absent" before it ends. Exports stream a file response (`HttpResponse` with `Content-Disposition: attachment`) rather than JSON. The frontend downloads these via `axios` with `responseType: "blob"` (not a plain `<a href>`, since the endpoint requires the `Authorization: Token` header, which a bare link can't send) and triggers a browser save via `URL.createObjectURL`.

**Tech Stack:** `openpyxl` (Excel), `reportlab` (PDF), stdlib `csv` — all new backend dependencies, installed this phase. No new frontend dependencies.

---

## File Structure

```text
backend/attendance/
├── services.py                # MODIFY — build_attendance_matrix(), get_closed_sessions()
├── views.py                     # MODIFY — StudentHistoryView, AnalyticsView, ExportCSVView, ExportExcelView, ExportPDFView
├── urls.py                        # MODIFY — 5 new routes
└── tests/
    ├── test_student_history.py      # NEW
    ├── test_analytics.py              # NEW
    └── test_exports.py                  # NEW

frontend/src/
├── api/client.ts                # MODIFY — getStudentHistory, getAnalytics, downloadReport
├── pages/
│   ├── student/
│   │   └── AttendanceHistoryPage.tsx  # NEW
│   ├── teacher/
│   │   └── AnalyticsPage.tsx            # NEW
│   ├── StudentProfilePage.tsx       # MODIFY — link to history page
│   └── TeacherProfilePage.tsx       # MODIFY — link to analytics page
└── App.tsx                       # MODIFY — new routes
```

---

## Task 1: Shared attendance-matrix service

**Files:**
- Modify: `backend/attendance/services.py`
- Test: `backend/attendance/tests/test_attendance_matrix.py`

- [ ] **Step 1: Write the failing test**

`backend/attendance/tests/test_attendance_matrix.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`, venv active): `python manage.py test attendance.tests.test_attendance_matrix -v 2`
Expected: FAIL — `ImportError: cannot import name 'build_attendance_matrix' from 'attendance.services'`.

- [ ] **Step 3: Add the service functions**

Read the CURRENT actual content of `backend/attendance/services.py` first. Append to it (keep everything else — `get_current_qr_token`, `broadcast_attendance_update`, `broadcast_activity_event`, `log_activity`, `mark_attendance` — exactly as it currently is):

```python
from accounts.models import User


def get_closed_sessions():
    return AttendanceSession.objects.filter(status=AttendanceSession.STATUS_CLOSED).order_by("date", "start_time")


def build_attendance_matrix():
    sessions = list(get_closed_sessions())
    students = (
        User.objects.filter(role=User.ROLE_STUDENT, student_profile__isnull=False)
        .select_related("student_profile")
        .order_by("student_profile__crn")
    )
    present_pairs = set(
        Attendance.objects.filter(session__in=sessions).values_list("student_id", "session_id")
    )
    rows = []
    for student in students:
        presents = {s.id: (student.id, s.id) in present_pairs for s in sessions}
        present_count = sum(presents.values())
        total = len(sessions)
        percentage = round((present_count / total) * 100, 1) if total else 0.0
        rows.append(
            {
                "student": student,
                "crn": student.student_profile.crn,
                "name": student.get_full_name() or student.username,
                "presents": presents,
                "present_count": present_count,
                "total": total,
                "percentage": percentage,
            }
        )
    return sessions, rows
```

Add the `from accounts.models import User` import at the TOP of the file, grouped with the other imports (not inline where shown above — that placement above is just to show you which lines are new; put the import in the proper top-of-file import block alongside `from attendance.models import ...`).

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test attendance.tests.test_attendance_matrix -v 2`
Expected: `OK` (3 tests pass).

- [ ] **Step 5: Run the full attendance suite**

Run: `python manage.py test attendance -v 2`
Expected: `OK` — no regressions.

- [ ] **Step 6: Commit**

```bash
git add backend/attendance/services.py backend/attendance/tests/test_attendance_matrix.py
git commit -m "feat: shared attendance-matrix service (closed sessions × students × present/absent)"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 2: Student attendance-history endpoint

**Files:**
- Modify: `backend/attendance/views.py`
- Modify: `backend/attendance/urls.py`
- Test: `backend/attendance/tests/test_student_history.py`

- [ ] **Step 1: Write the failing test**

`backend/attendance/tests/test_student_history.py`:

```python
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from attendance.models import AttendanceSession, Attendance

User = get_user_model()


class StudentHistoryTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.student = User.objects.create_user(username="stud", password="pw12345678", role=User.ROLE_STUDENT)
        self.teacher_token = Token.objects.create(user=self.teacher)
        self.student_token = Token.objects.create(user=self.student)
        self.closed1 = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI", status=AttendanceSession.STATUS_CLOSED
        )
        self.closed2 = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI", status=AttendanceSession.STATUS_CLOSED
        )
        AttendanceSession.objects.create(teacher=self.teacher, subject="AI", status=AttendanceSession.STATUS_ACTIVE)
        Attendance.objects.create(student=self.student, session=self.closed1)

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_requires_student_role(self):
        self._auth(self.teacher_token)
        response = self.client.get(reverse("student-attendance-history"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_correct_totals_and_history(self):
        self._auth(self.student_token)
        response = self.client.get(reverse("student-attendance-history"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 2)
        self.assertEqual(response.data["present"], 1)
        self.assertEqual(response.data["percentage"], 50.0)
        self.assertEqual(len(response.data["history"]), 2)
        statuses = {h["subject"]: h["status"] for h in response.data["history"]}
        self.assertIn("present", statuses.values())
        self.assertIn("absent", statuses.values())
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`, venv active): `python manage.py test attendance.tests.test_student_history -v 2`
Expected: FAIL — `NoReverseMatch` for `"student-attendance-history"`.

- [ ] **Step 3: Add the view**

Read the CURRENT actual content of `backend/attendance/views.py` first. Append (merge `get_closed_sessions` into the existing `from attendance.services import get_current_qr_token, mark_attendance` import line):

```python
class StudentHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def get(self, request):
        sessions = get_closed_sessions()
        present_session_ids = set(
            Attendance.objects.filter(student=request.user, session__in=sessions).values_list(
                "session_id", flat=True
            )
        )
        history = [
            {
                "date": s.date,
                "subject": s.subject,
                "status": "present" if s.id in present_session_ids else "absent",
            }
            for s in sessions
        ]
        total = len(history)
        present = len(present_session_ids)
        percentage = round((present / total) * 100, 1) if total else 0.0
        return Response({"total": total, "present": present, "percentage": percentage, "history": history})
```

- [ ] **Step 4: Wire URL**

Read the CURRENT actual content of `backend/attendance/urls.py` first. Add `StudentHistoryView` to the import block and one new route (keep the existing six untouched):

```python
path("student/history/", StudentHistoryView.as_view(), name="student-attendance-history"),
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python manage.py test attendance.tests.test_student_history -v 2`
Expected: `OK` (2 tests pass).

- [ ] **Step 6: Commit**

```bash
git add backend/attendance/views.py backend/attendance/urls.py backend/attendance/tests/test_student_history.py
git commit -m "feat: student attendance-history endpoint (closed sessions only)"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 3: Teacher analytics endpoint

**Files:**
- Modify: `backend/attendance/views.py`
- Modify: `backend/attendance/urls.py`
- Test: `backend/attendance/tests/test_analytics.py`

- [ ] **Step 1: Write the failing test**

`backend/attendance/tests/test_analytics.py`:

```python
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from accounts.models import StudentProfile
from attendance.models import AttendanceSession, Attendance

User = get_user_model()


class AnalyticsTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.teacher_token = Token.objects.create(user=self.teacher)
        self.student_token = Token.objects.create(
            user=User.objects.create_user(username="stud0", password="pw12345678", role=User.ROLE_STUDENT)
        )

        self.s1 = User.objects.create_user(
            username="stud1", password="pw12345678", role=User.ROLE_STUDENT, first_name="Aman Raj"
        )
        StudentProfile.objects.create(user=self.s1, crn="101", course="CSE", semester=5, section="A")
        self.s2 = User.objects.create_user(
            username="stud2", password="pw12345678", role=User.ROLE_STUDENT, first_name="Priya Singh"
        )
        StudentProfile.objects.create(user=self.s2, crn="102", course="CSE", semester=5, section="A")

        self.closed1 = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI", status=AttendanceSession.STATUS_CLOSED
        )
        self.closed2 = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI", status=AttendanceSession.STATUS_CLOSED
        )
        Attendance.objects.create(student=self.s1, session=self.closed1)
        Attendance.objects.create(student=self.s1, session=self.closed2)
        Attendance.objects.create(student=self.s2, session=self.closed1)

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_requires_teacher_role(self):
        self._auth(self.student_token)
        response = self.client.get(reverse("attendance-analytics"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_overall_and_per_student_breakdown(self):
        self._auth(self.teacher_token)
        response = self.client.get(reverse("attendance-analytics"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_sessions"], 2)
        self.assertEqual(response.data["total_students"], 2)
        self.assertEqual(response.data["overall_rate"], 75.0)
        self.assertEqual(len(response.data["students"]), 2)

    def test_below_threshold_list(self):
        self._auth(self.teacher_token)
        response = self.client.get(reverse("attendance-analytics"))
        below = response.data["below_threshold"]
        self.assertEqual(len(below), 1)
        self.assertEqual(below[0]["crn"], "102")
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`, venv active): `python manage.py test attendance.tests.test_analytics -v 2`
Expected: FAIL — `NoReverseMatch` for `"attendance-analytics"`.

- [ ] **Step 3: Add the view**

Append to `backend/attendance/views.py` (merge `build_attendance_matrix` into the existing services import line):

```python
class AnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request):
        sessions, rows = build_attendance_matrix()
        total_sessions = len(sessions)
        total_students = len(rows)
        overall_present = sum(r["present_count"] for r in rows)
        overall_possible = total_students * total_sessions
        overall_rate = round((overall_present / overall_possible) * 100, 1) if overall_possible else 0.0
        students_data = [
            {
                "name": r["name"],
                "crn": r["crn"],
                "present": r["present_count"],
                "total": r["total"],
                "percentage": r["percentage"],
            }
            for r in rows
        ]
        below_threshold = [s for s in students_data if s["percentage"] < 75]
        return Response(
            {
                "total_sessions": total_sessions,
                "total_students": total_students,
                "overall_rate": overall_rate,
                "students": students_data,
                "below_threshold": below_threshold,
            }
        )
```

- [ ] **Step 4: Wire URL**

Add `AnalyticsView` to `backend/attendance/urls.py`'s import block and one new route:

```python
path("analytics/", AnalyticsView.as_view(), name="attendance-analytics"),
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python manage.py test attendance.tests.test_analytics -v 2`
Expected: `OK` (3 tests pass).

- [ ] **Step 6: Commit**

```bash
git add backend/attendance/views.py backend/attendance/urls.py backend/attendance/tests/test_analytics.py
git commit -m "feat: teacher analytics endpoint (overall rate, per-student, below-threshold)"
```

**Do NOT add a "Co-Authored-By" trailer.**

Note: this endpoint aggregates ALL closed sessions and ALL students system-wide, regardless of which teacher created which session — acceptable under ClassPulse v1's single-teacher/single-class scope (doc.md §4), but would leak cross-teacher data if multiple teachers each ran independent classes. Flag this in the Work Log as a known v1 limitation, not something to fix now.

---

## Task 4: CSV export endpoint

**Files:**
- Modify: `backend/attendance/views.py`
- Modify: `backend/attendance/urls.py`
- Test: `backend/attendance/tests/test_exports.py`

- [ ] **Step 1: Write the failing test**

`backend/attendance/tests/test_exports.py`:

```python
import csv
import io

from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from accounts.models import StudentProfile
from attendance.models import AttendanceSession, Attendance

User = get_user_model()


class ExportTest(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.teacher_token = Token.objects.create(user=self.teacher)
        self.student_token = Token.objects.create(
            user=User.objects.create_user(username="stud0", password="pw12345678", role=User.ROLE_STUDENT)
        )
        self.s1 = User.objects.create_user(
            username="stud1", password="pw12345678", role=User.ROLE_STUDENT, first_name="Aman Raj"
        )
        StudentProfile.objects.create(user=self.s1, crn="101", course="CSE", semester=5, section="A")
        self.closed = AttendanceSession.objects.create(
            teacher=self.teacher, subject="AI", status=AttendanceSession.STATUS_CLOSED
        )
        Attendance.objects.create(student=self.s1, session=self.closed)

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_csv_requires_teacher_role(self):
        self._auth(self.student_token)
        response = self.client.get(reverse("export-csv"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_csv_export_shape(self):
        self._auth(self.teacher_token)
        response = self.client.get(reverse("export-csv"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])

        content = response.content.decode("utf-8")
        rows = list(csv.reader(io.StringIO(content)))
        header = rows[0]
        self.assertEqual(header[0], "CRN")
        self.assertEqual(header[1], "Name")
        self.assertEqual(header[-1], "%")
        data_row = rows[1]
        self.assertEqual(data_row[0], "101")
        self.assertEqual(data_row[-1], "100.0")
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`, venv active): `python manage.py test attendance.tests.test_exports.ExportTest.test_csv_export_shape -v 2`
Expected: FAIL — `NoReverseMatch` for `"export-csv"`.

- [ ] **Step 3: Add the view**

Append to `backend/attendance/views.py`. Add `import csv` and `from django.http import HttpResponse` to the top-of-file import block first, then append the view:

```python
class ExportCSVView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request):
        sessions, rows = build_attendance_matrix()
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=attendance_report.csv"
        writer = csv.writer(response)
        header = ["CRN", "Name"] + [s.date.isoformat() for s in sessions] + ["%"]
        writer.writerow(header)
        for r in rows:
            row = (
                [r["crn"], r["name"]]
                + ["P" if r["presents"][s.id] else "A" for s in sessions]
                + [str(r["percentage"])]
            )
            writer.writerow(row)
        return response
```

- [ ] **Step 4: Wire URL**

Add `ExportCSVView` to `backend/attendance/urls.py`'s import block and one new route:

```python
path("export/csv/", ExportCSVView.as_view(), name="export-csv"),
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python manage.py test attendance.tests.test_exports -v 2`
Expected: `OK` (2 tests pass).

- [ ] **Step 6: Commit**

```bash
git add backend/attendance/views.py backend/attendance/urls.py backend/attendance/tests/test_exports.py
git commit -m "feat: CSV attendance-report export"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 5: Excel export endpoint

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/attendance/views.py`
- Modify: `backend/attendance/urls.py`
- Modify: `backend/attendance/tests/test_exports.py`

- [ ] **Step 1: Install openpyxl**

Run (from `backend/`, venv active):

```
pip install openpyxl
pip freeze > requirements.txt
```

- [ ] **Step 2: Write the failing test**

Add to `backend/attendance/tests/test_exports.py` (append to the existing `ExportTest` class — don't restructure the CSV tests):

```python
    def test_excel_export_shape(self):
        from openpyxl import load_workbook
        import io as io_module

        self._auth(self.teacher_token)
        response = self.client.get(reverse("export-excel"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn("attachment", response["Content-Disposition"])

        wb = load_workbook(io_module.BytesIO(response.content))
        ws = wb.active
        header = [cell.value for cell in ws[1]]
        self.assertEqual(header[0], "CRN")
        self.assertEqual(header[-1], "%")
        data_row = [cell.value for cell in ws[2]]
        self.assertEqual(data_row[0], "101")
```

- [ ] **Step 3: Run test to verify it fails**

Run (from `backend/`, venv active): `python manage.py test attendance.tests.test_exports.ExportTest.test_excel_export_shape -v 2`
Expected: FAIL — `NoReverseMatch` for `"export-excel"`.

- [ ] **Step 4: Add the view**

Append to `backend/attendance/views.py`. Add `from io import BytesIO` and `from openpyxl import Workbook` to the top-of-file import block, then append:

```python
class ExportExcelView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request):
        sessions, rows = build_attendance_matrix()
        wb = Workbook()
        ws = wb.active
        ws.title = "Attendance"
        header = ["CRN", "Name"] + [s.date.isoformat() for s in sessions] + ["%"]
        ws.append(header)
        for r in rows:
            row = (
                [r["crn"], r["name"]]
                + ["P" if r["presents"][s.id] else "A" for s in sessions]
                + [r["percentage"]]
            )
            ws.append(row)
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        response = HttpResponse(
            buffer.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = "attachment; filename=attendance_report.xlsx"
        return response
```

- [ ] **Step 5: Wire URL**

Add `ExportExcelView` to `backend/attendance/urls.py`'s import block and one new route:

```python
path("export/excel/", ExportExcelView.as_view(), name="export-excel"),
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python manage.py test attendance.tests.test_exports -v 2`
Expected: `OK` (3 tests pass).

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt backend/attendance/views.py backend/attendance/urls.py backend/attendance/tests/test_exports.py
git commit -m "feat: Excel attendance-report export"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 6: PDF export endpoint

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/attendance/views.py`
- Modify: `backend/attendance/urls.py`
- Modify: `backend/attendance/tests/test_exports.py`

- [ ] **Step 1: Install reportlab**

Run (from `backend/`, venv active):

```
pip install reportlab
pip freeze > requirements.txt
```

- [ ] **Step 2: Write the failing test**

Add to `backend/attendance/tests/test_exports.py` (append to `ExportTest`):

```python
    def test_pdf_export_shape(self):
        self._auth(self.teacher_token)
        response = self.client.get(reverse("export-pdf"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))
```

- [ ] **Step 3: Run test to verify it fails**

Run (from `backend/`, venv active): `python manage.py test attendance.tests.test_exports.ExportTest.test_pdf_export_shape -v 2`
Expected: FAIL — `NoReverseMatch` for `"export-pdf"`.

- [ ] **Step 4: Add the view**

Append to `backend/attendance/views.py`. Add these imports to the top-of-file block:

```python
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
```

Then append:

```python
class ExportPDFView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request):
        sessions, rows = build_attendance_matrix()
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        header = ["CRN", "Name"] + [s.date.isoformat() for s in sessions] + ["%"]
        data = [header]
        for r in rows:
            data.append(
                [r["crn"], r["name"]]
                + ["P" if r["presents"][s.id] else "A" for s in sessions]
                + [str(r["percentage"])]
            )
        table = Table(data)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ]
            )
        )
        doc.build([table])
        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type="application/pdf")
        response["Content-Disposition"] = "attachment; filename=attendance_report.pdf"
        return response
```

(`BytesIO` is already imported from Task 5.)

- [ ] **Step 5: Wire URL**

Add `ExportPDFView` to `backend/attendance/urls.py`'s import block and one new route:

```python
path("export/pdf/", ExportPDFView.as_view(), name="export-pdf"),
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python manage.py test attendance.tests.test_exports -v 2`
Expected: `OK` (4 tests pass).

- [ ] **Step 7: Run the full attendance suite**

Run: `python manage.py test attendance -v 2`
Expected: `OK` — no regressions.

- [ ] **Step 8: Commit**

```bash
git add backend/requirements.txt backend/attendance/views.py backend/attendance/urls.py backend/attendance/tests/test_exports.py
git commit -m "feat: PDF attendance-report export"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 7: Backend sanity check

**Files:** none new — this task verifies everything wired in Tasks 1-6

- [ ] **Step 1: Run the full backend test suite**

Run (from `backend/`, venv active): `python manage.py test -v 2`
Expected: `OK` — all tests pass, no failures, no errors. Report the ACTUAL total count.

- [ ] **Step 2: Confirm `manage.py check` is clean**

Run: `python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 3: Commit**

Only if Steps 1-2 needed a fix — otherwise skip the commit and move to Task 8.

---

## Task 8: Frontend — student attendance-history page

**Files:**
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/pages/student/AttendanceHistoryPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/StudentProfilePage.tsx`

- [ ] **Step 1: Add the API call**

Add to `frontend/src/api/client.ts` (append at the end, after `getSessionActivity`; keep all existing exports untouched):

```ts
export interface AttendanceHistoryEntry {
  date: string;
  subject: string;
  status: "present" | "absent";
}

export interface AttendanceHistoryResponse {
  total: number;
  present: number;
  percentage: number;
  history: AttendanceHistoryEntry[];
}

export async function getStudentHistory(): Promise<AttendanceHistoryResponse> {
  const { data } = await api.get<AttendanceHistoryResponse>("/attendance/student/history/");
  return data;
}
```

- [ ] **Step 2: Create the page**

`frontend/src/pages/student/AttendanceHistoryPage.tsx`:

```tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Container, Spinner, Table, Badge } from "react-bootstrap";
import { getStudentHistory, logout } from "../../api/client";
import type { AttendanceHistoryResponse } from "../../api/client";

export default function AttendanceHistoryPage() {
  const [data, setData] = useState<AttendanceHistoryResponse | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    getStudentHistory()
      .then(setData)
      .catch(() => {
        logout();
        navigate("/login", { replace: true });
      });
  }, [navigate]);

  if (!data) return <Spinner animation="border" className="m-4" />;

  return (
    <Container className="py-4">
      <h2>Attendance History</h2>
      <p className="mb-1">Total Classes: {data.total}</p>
      <p className="mb-1">Present: {data.present}</p>
      <p className="mb-3">
        Attendance: <Badge bg={data.percentage >= 75 ? "success" : "danger"}>{data.percentage}%</Badge>
      </p>
      <Table striped bordered>
        <thead>
          <tr>
            <th>Date</th>
            <th>Subject</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {data.history.map((entry, index) => (
            <tr key={`${entry.date}-${index}`}>
              <td>{entry.date}</td>
              <td>{entry.subject}</td>
              <td>
                <Badge bg={entry.status === "present" ? "success" : "danger"}>{entry.status}</Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Container>
  );
}
```

- [ ] **Step 3: Add the route**

Read `frontend/src/App.tsx` first. Add an import (`import AttendanceHistoryPage from "./pages/student/AttendanceHistoryPage";`) and a new route inside the `<ProtectedRoute>` block, alongside the existing `/student/profile` and `/student/scan` routes, before the catch-all:

```tsx
<Route path="/student/history" element={<AttendanceHistoryPage />} />
```

- [ ] **Step 4: Add a link from StudentProfilePage**

Read `frontend/src/pages/StudentProfilePage.tsx` first. Add a `<Link to="/student/history" className="btn btn-outline-primary mt-2 ms-2">` (or similar, matching whatever `Link`/button pattern the file already uses for its existing "Scan Attendance QR" link — reuse the same import if `Link` is already imported) right after the existing "Scan Attendance QR" link:

```tsx
<Link to="/student/history" className="btn btn-outline-primary mt-2 ms-2">
  Attendance History
</Link>
```

- [ ] **Step 5: Verify it builds**

Run `npm run build` from `frontend/`. Expected: no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/pages/student/AttendanceHistoryPage.tsx frontend/src/App.tsx frontend/src/pages/StudentProfilePage.tsx
git commit -m "feat: student attendance-history page"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Task 9: Frontend — teacher analytics page with exports

**Files:**
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/pages/teacher/AnalyticsPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/TeacherProfilePage.tsx`

- [ ] **Step 1: Add the API calls**

Add to `frontend/src/api/client.ts` (append at the end, after `getStudentHistory`):

```ts
export interface StudentAnalyticsRow {
  name: string;
  crn: string;
  present: number;
  total: number;
  percentage: number;
}

export interface AnalyticsResponse {
  total_sessions: number;
  total_students: number;
  overall_rate: number;
  students: StudentAnalyticsRow[];
  below_threshold: StudentAnalyticsRow[];
}

export async function getAnalytics(): Promise<AnalyticsResponse> {
  const { data } = await api.get<AnalyticsResponse>("/attendance/analytics/");
  return data;
}

export async function downloadReport(format: "csv" | "excel" | "pdf"): Promise<void> {
  const response = await api.get(`/attendance/export/${format}/`, { responseType: "blob" });
  const extension = format === "excel" ? "xlsx" : format;
  const blob = new Blob([response.data]);
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `attendance_report.${extension}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
```

- [ ] **Step 2: Create the page**

`frontend/src/pages/teacher/AnalyticsPage.tsx`:

```tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Container, Spinner, Table, Badge, Button, ButtonGroup, Alert } from "react-bootstrap";
import { getAnalytics, downloadReport, logout } from "../../api/client";
import type { AnalyticsResponse } from "../../api/client";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    getAnalytics()
      .then(setData)
      .catch(() => {
        logout();
        navigate("/login", { replace: true });
      });
  }, [navigate]);

  const handleDownload = async (format: "csv" | "excel" | "pdf") => {
    setDownloadError(null);
    try {
      await downloadReport(format);
    } catch {
      setDownloadError("Could not download the report. Please try again.");
    }
  };

  if (!data) return <Spinner animation="border" className="m-4" />;

  return (
    <Container className="py-4">
      <h2>Attendance Analytics</h2>
      <p className="mb-1">Total Sessions: {data.total_sessions}</p>
      <p className="mb-1">Total Students: {data.total_students}</p>
      <p className="mb-3">
        Overall Rate: <Badge bg="info">{data.overall_rate}%</Badge>
      </p>

      {downloadError && <Alert variant="danger">{downloadError}</Alert>}
      <ButtonGroup className="mb-3">
        <Button variant="outline-secondary" onClick={() => handleDownload("csv")}>
          Export CSV
        </Button>
        <Button variant="outline-secondary" onClick={() => handleDownload("excel")}>
          Export Excel
        </Button>
        <Button variant="outline-secondary" onClick={() => handleDownload("pdf")}>
          Export PDF
        </Button>
      </ButtonGroup>

      {data.below_threshold.length > 0 && (
        <Alert variant="warning">
          {data.below_threshold.length} student(s) below 75% attendance:{" "}
          {data.below_threshold.map((s) => s.name).join(", ")}
        </Alert>
      )}

      <Table striped bordered>
        <thead>
          <tr>
            <th>CRN</th>
            <th>Name</th>
            <th>Present</th>
            <th>Total</th>
            <th>%</th>
          </tr>
        </thead>
        <tbody>
          {data.students.map((s) => (
            <tr key={s.crn}>
              <td>{s.crn}</td>
              <td>{s.name}</td>
              <td>{s.present}</td>
              <td>{s.total}</td>
              <td>
                <Badge bg={s.percentage >= 75 ? "success" : "danger"}>{s.percentage}%</Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Container>
  );
}
```

- [ ] **Step 3: Add the route**

Read `frontend/src/App.tsx` first. Add an import (`import AnalyticsPage from "./pages/teacher/AnalyticsPage";`) and a new route inside the `<ProtectedRoute>` block, alongside the other teacher routes, before the catch-all:

```tsx
<Route path="/teacher/analytics" element={<AnalyticsPage />} />
```

- [ ] **Step 4: Add a link from TeacherProfilePage**

Read `frontend/src/pages/TeacherProfilePage.tsx` first. Add a link to `/teacher/analytics` next to the existing "Start Attendance" link, matching whatever pattern that link uses:

```tsx
<Link to="/teacher/analytics" className="btn btn-outline-primary ms-2">
  Analytics
</Link>
```

- [ ] **Step 5: Verify it builds**

Run `npm run build` from `frontend/`. Expected: no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/pages/teacher/AnalyticsPage.tsx frontend/src/App.tsx frontend/src/pages/TeacherProfilePage.tsx
git commit -m "feat: teacher analytics page with CSV/Excel/PDF export"
```

**Do NOT add a "Co-Authored-By" trailer.**

---

## Phase 5 Exit Criteria (from docs/plan.md)

- [ ] Student sees correct running attendance percentage and full history.
- [ ] Teacher downloads an XLSX/CSV/PDF attendance report matching the on-screen analytics data.
- [ ] Teacher sees overall rate, per-student breakdown, and a below-threshold list.
- [ ] Percentage formula matches doc.md §21 exactly: `(present / total) × 100`.

## After Completion

Update the Work Log in [`Agent.md`](../../../Agent.md) with a new entry noting Phase 5 is complete. All 5 phases from `docs/plan.md`'s Version 1 Development Plan are now done — the next step is manual end-to-end verification (register → login → start session → scan → live dashboard → close session → history/analytics/export), not a new phase, unless the user asks for one of the Future Enhancements (doc.md §33).
