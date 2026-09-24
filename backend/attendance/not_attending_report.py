from accounts.models import StudentProfile
from attendance.models import NotAttendingMark


def build_not_attending_report(section: str = "", date_from=None, date_to=None) -> dict:
    """Every student with at least one "not attending" mark in range, grouped
    by student, newest mark first — the admin-facing list for Attendance
    Analytics. Mirrors `build_late_report`'s shape/conventions.
    """
    marks = NotAttendingMark.objects.select_related("student", "student__student_profile")
    if section:
        marks = marks.filter(section=section)
    if date_from:
        marks = marks.filter(date__gte=date_from)
    if date_to:
        marks = marks.filter(date__lte=date_to)

    by_student = {}
    for mark in marks:
        profile = getattr(mark.student, "student_profile", None)
        if profile is None:
            continue
        entry = by_student.setdefault(
            mark.student_id,
            {
                "name": mark.student.get_full_name() or mark.student.username,
                "crn": profile.crn,
                "section": mark.section,
                "dates": [],
            },
        )
        entry["dates"].append(mark.date.isoformat())

    students = []
    for entry in by_student.values():
        entry["dates"].sort(reverse=True)
        entry["count"] = len(entry["dates"])
        students.append(entry)
    students.sort(key=lambda e: (-e["count"], e["crn"]))

    sections = {}
    for entry in students:
        bucket = sections.setdefault(entry["section"], {"section": entry["section"], "students": 0, "marks": 0})
        bucket["students"] += 1
        bucket["marks"] += entry["count"]

    return {
        "total_marks": sum(e["count"] for e in students),
        "sections": sorted(sections.values(), key=lambda b: b["section"]),
        "students": students,
    }
