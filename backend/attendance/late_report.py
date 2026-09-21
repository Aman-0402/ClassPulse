from django.utils import timezone

from attendance.models import Attendance
from attendance.services import get_closed_sessions

# Teacher-entered attendance is stamped with this device_info (see ManualAttendanceView).
MANUAL_DEVICE_INFO = "manual override by teacher"

# "Regularly late": late at least this many times AND for at least this share of scans.
REGULAR_MIN_LATE = 3
REGULAR_MIN_RATE = 50.0


def build_late_report(section: str = "", date_from=None, date_to=None, min_minutes: int = 10) -> dict:
    """Who scanned in late, and how late.

    "Late" = minutes between the session starting (the teacher opening the QR)
    and the student's own scan. Teacher-entered manual attendance is skipped -
    its timestamp is when the teacher clicked, not when the student turned up.
    min_minutes=0 lists every scan time.
    """
    sessions = list(get_closed_sessions(date_from=date_from, date_to=date_to))
    records = (
        Attendance.objects.filter(session__in=sessions)
        .exclude(device_info=MANUAL_DEVICE_INFO)
        .select_related("session", "student", "student__student_profile")
    )
    if section:
        records = records.filter(student__student_profile__section=section)

    by_student = {}
    scans_by_student = {}
    total_scans = 0
    for record in records:
        profile = getattr(record.student, "student_profile", None)
        if profile is None:
            continue
        total_scans += 1
        scans_by_student[record.student_id] = scans_by_student.get(record.student_id, 0) + 1
        minutes_late = max(0.0, (record.marked_at - record.session.start_time).total_seconds() / 60)
        if minutes_late < min_minutes:
            continue
        entry = by_student.setdefault(
            record.student_id,
            {
                "name": record.student.get_full_name() or record.student.username,
                "crn": profile.crn,
                "section": profile.section,
                "entries": [],
            },
        )
        entry["entries"].append(
            {
                "date": record.session.date,
                "subject": record.session.subject,
                "scanned_at": timezone.localtime(record.marked_at).isoformat(),
                "minutes_late": round(minutes_late, 1),
            }
        )

    students = []
    for student_id, entry in by_student.items():
        entry["entries"].sort(key=lambda e: e["scanned_at"], reverse=True)
        delays = [e["minutes_late"] for e in entry["entries"]]
        entry["late_count"] = len(delays)
        entry["max_late"] = max(delays)
        entry["avg_late"] = round(sum(delays) / len(delays), 1)
        entry["scan_count"] = scans_by_student[student_id]
        # Share of this student's scans that were late - what separates "late once"
        # from "regularly late".
        entry["late_rate"] = round(entry["late_count"] / entry["scan_count"] * 100, 1)
        entry["regular"] = entry["late_count"] >= REGULAR_MIN_LATE and entry["late_rate"] >= REGULAR_MIN_RATE
        students.append(entry)
    students.sort(key=lambda e: (-e["late_count"], -e["max_late"], e["crn"]))

    sections = {}
    for entry in students:
        bucket = sections.setdefault(
            entry["section"], {"section": entry["section"], "late_students": 0, "late_scans": 0}
        )
        bucket["late_students"] += 1
        bucket["late_scans"] += entry["late_count"]

    return {
        "min_minutes": min_minutes,
        "total_scans": total_scans,
        "late_scans": sum(e["late_count"] for e in students),
        "sections": sorted(sections.values(), key=lambda b: b["section"]),
        "students": students,
    }
