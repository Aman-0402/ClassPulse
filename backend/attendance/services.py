import logging
from typing import NamedTuple

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from attendance.exceptions import (
    DuplicateAttendanceError,
    ExpiredTokenError,
    InvalidTokenError,
    SessionClosedError,
    WrongSectionError,
)
from accounts.models import User, StudentProfile
from attendance.models import ActivityLog, AttendanceSession, ClassSchedule, QRToken, Attendance

logger = logging.getLogger(__name__)


def close_session_if_window_expired(session: AttendanceSession) -> AttendanceSession:
    """Lazily auto-close a session once its attendance window has elapsed.

    Mirrors the QR-token lazy-rotation pattern already used in this app: there's no
    background scheduler, so expiry is enforced the next time anything touches the
    session (marking attendance, fetching the QR, loading the live dashboard) rather
    than on a timer. A manual "Stop Attendance" click still closes it immediately;
    this only covers the case where the teacher's window runs out unattended.
    """
    if session.status == AttendanceSession.STATUS_ACTIVE and session.is_window_expired():
        session.status = AttendanceSession.STATUS_CLOSED
        session.end_time = session.closes_at
        session.save(update_fields=["status", "end_time"])
    return session


def get_current_qr_token(session: AttendanceSession) -> QRToken:
    latest = session.qr_tokens.order_by("-created_at", "-id").first()
    if latest and not latest.is_expired():
        return latest
    return QRToken.objects.create(session=session)


def broadcast_attendance_update(attendance):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    profile = getattr(attendance.student, "student_profile", None)
    present_count = Attendance.objects.filter(session=attendance.session).count()
    try:
        async_to_sync(channel_layer.group_send)(
            f"attendance_session_{attendance.session_id}",
            {
                "type": "attendance.update",
                "data": {
                    "kind": "attendance",
                    "name": attendance.student.get_full_name() or attendance.student.username,
                    "crn": profile.crn if profile else "",
                    "photo": (
                        settings.BACKEND_ORIGIN + profile.photo.url if profile and profile.photo else None
                    ),
                    "marked_at": attendance.marked_at.isoformat(),
                    "present_count": present_count,
                },
            },
        )
    except Exception:
        logger.exception("Failed to broadcast attendance update for attendance id=%s", attendance.id)


def broadcast_activity_event(log_entry):
    if log_entry.session_id is None:
        return
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    try:
        async_to_sync(channel_layer.group_send)(
            f"attendance_session_{log_entry.session_id}",
            {
                "type": "activity.update",
                "data": {
                    "kind": "activity",
                    "activity_type": log_entry.activity_type,
                    "student": log_entry.student.get_full_name() or log_entry.student.username,
                    "created_at": log_entry.created_at.isoformat(),
                },
            },
        )
    except Exception:
        logger.exception("Failed to broadcast activity event id=%s", log_entry.id)


def log_activity(student, session, activity_type, ip_address="", device_info=""):
    try:
        entry = ActivityLog.objects.create(
            student=student,
            session=session,
            activity_type=activity_type,
            ip_address=ip_address or None,
            device_info=device_info,
        )
    except Exception:
        logger.exception(
            "Failed to write ActivityLog for student id=%s activity_type=%s", getattr(student, "id", None), activity_type
        )
        return None
    if activity_type != ActivityLog.TYPE_SUCCESS:
        broadcast_activity_event(entry)
    return entry


def mark_attendance(student, token_value, ip_address, device_info):
    try:
        qr_token = QRToken.objects.select_related("session").get(token=token_value)
    except QRToken.DoesNotExist:
        log_activity(student, None, ActivityLog.TYPE_INVALID_TOKEN, ip_address, device_info)
        raise InvalidTokenError()

    session = close_session_if_window_expired(qr_token.session)

    if session.status != AttendanceSession.STATUS_ACTIVE:
        log_activity(student, session, ActivityLog.TYPE_SESSION_CLOSED, ip_address, device_info)
        raise SessionClosedError()

    student_section = getattr(getattr(student, "student_profile", None), "section", "")
    if session.section and student_section != session.section:
        log_activity(student, session, ActivityLog.TYPE_WRONG_SECTION, ip_address, device_info)
        raise WrongSectionError(session.section)

    if qr_token.is_expired():
        log_activity(student, session, ActivityLog.TYPE_EXPIRED_TOKEN, ip_address, device_info)
        raise ExpiredTokenError()

    if Attendance.objects.filter(student=student, session=session).exists():
        log_activity(student, session, ActivityLog.TYPE_DUPLICATE, ip_address, device_info)
        raise DuplicateAttendanceError()

    try:
        with transaction.atomic():
            attendance = Attendance.objects.create(
                student=student, session=session, ip_address=ip_address or None, device_info=device_info
            )
    except IntegrityError:
        log_activity(student, session, ActivityLog.TYPE_DUPLICATE, ip_address, device_info)
        raise DuplicateAttendanceError()

    previous_device = (
        ActivityLog.objects.filter(student=student, activity_type=ActivityLog.TYPE_SUCCESS)
        .exclude(device_info="")
        .order_by("-created_at")
        .values_list("device_info", flat=True)
        .first()
    )
    if previous_device and device_info and previous_device != device_info:
        log_activity(student, session, ActivityLog.TYPE_NEW_DEVICE, ip_address, device_info)

    log_activity(student, session, ActivityLog.TYPE_SUCCESS, ip_address, device_info)
    broadcast_attendance_update(attendance)
    return attendance


def set_manual_attendance(session, student, present, device_info=""):
    """Teacher-initiated correction — bypasses QR/section checks by design.

    A teacher marking someone present/absent by hand is an authorized override,
    not a suspicious event, so this doesn't go through ActivityLog the way scans
    do; it just creates or removes the Attendance row directly.
    """
    if present:
        attendance, created = Attendance.objects.get_or_create(
            student=student, session=session, defaults={"device_info": device_info or "manual override"}
        )
        if created:
            broadcast_attendance_update(attendance)
    else:
        Attendance.objects.filter(student=student, session=session).delete()


def get_session_roster(session):
    """Every student in this session's section, present/absent for THIS session specifically.

    Unlike get_day_attendance (section+date, "attended ANY session that day"), this is
    scoped to one exact session — what the live dashboard needs while a session is in
    progress. Returns [] for sessions started without a section (nothing to scope to).
    """
    if not session.section:
        return []
    students = (
        User.objects.filter(role=User.ROLE_STUDENT, student_profile__section=session.section)
        .select_related("student_profile")
        .order_by("student_profile__crn")
    )
    present_student_ids = set(
        Attendance.objects.filter(session=session).values_list("student_id", flat=True)
    )
    return [
        {
            "crn": student.student_profile.crn,
            "roll_number": student.student_profile.urn,
            "name": student.get_full_name() or student.username,
            "present": student.id in present_student_ids,
        }
        for student in students
    ]


def get_day_attendance(section, date):
    """Per-student present/absent for a specific section on a specific date.

    A student counts as present if they attended ANY of that section's sessions
    on that date (usually one, but a teacher could start an extra ad-hoc session
    the same day) — mirrors the "attended this session" semantics used everywhere
    else rather than introducing a new per-slot concept.
    """
    sessions = list(
        AttendanceSession.objects.filter(section=section, date=date).order_by("start_time")
    )
    students = (
        User.objects.filter(role=User.ROLE_STUDENT, student_profile__section=section)
        .select_related("student_profile")
        .order_by("student_profile__crn")
    )
    present_student_ids = set(
        Attendance.objects.filter(session__in=sessions).values_list("student_id", flat=True)
    )
    rows = [
        {
            "crn": student.student_profile.crn,
            "roll_number": student.student_profile.urn,
            "name": student.get_full_name() or student.username,
            "present": student.id in present_student_ids,
        }
        for student in students
    ]
    return sessions, rows


def get_available_sections():
    return list(
        StudentProfile.objects.exclude(section="")
        .order_by("section")
        .values_list("section", flat=True)
        .distinct()
    )


def get_today_schedule():
    """All timetable slots for today's weekday, in order."""
    today = timezone.localdate()
    return ClassSchedule.objects.filter(day_of_week=today.weekday()).order_by("start_time")


def merge_consecutive_slots(slots):
    """Collapse back-to-back periods for the same section/subject into one block.

    Two periods are the same class continued (e.g. 10:05-10:55 and 11:05-11:55 for
    BBA III D) when they're adjacent in the day's ordered timetable and share a
    section and subject — the real timetable leaves a short break between periods
    (10:55 to 11:05), so this merges on adjacency, not on an exact zero-gap
    boundary. Merging means a teacher sees "10:05 AM - 11:55 AM" once instead of
    two separate rows, and one attendance session naturally covers the double
    period.
    """
    merged = []
    for slot in slots:
        if merged and merged[-1]["section"] == slot.section and merged[-1]["subject"] == slot.subject:
            merged[-1]["end_time"] = slot.end_time
            merged[-1]["periods"] += 1
        else:
            merged.append(
                {
                    "subject": slot.subject,
                    "section": slot.section,
                    "start_time": slot.start_time,
                    "end_time": slot.end_time,
                    "periods": 1,
                }
            )
    return merged


def get_today_sessions_by_section(teacher):
    """This teacher's sessions started today, keyed by section (single slot per section per day)."""
    today = timezone.localdate()
    sessions = AttendanceSession.objects.filter(teacher=teacher, date=today).exclude(section="")
    return {session.section: session for session in sessions}


def get_current_schedule_slot():
    """The timetable slot covering right now, if any (local time, current weekday)."""
    now = timezone.localtime()
    return ClassSchedule.objects.filter(
        day_of_week=now.weekday(), start_time__lte=now.time(), end_time__gt=now.time()
    ).first()


def get_closed_sessions(date_from=None, date_to=None):
    sessions = AttendanceSession.objects.filter(status=AttendanceSession.STATUS_CLOSED)
    if date_from:
        sessions = sessions.filter(date__gte=date_from)
    if date_to:
        sessions = sessions.filter(date__lte=date_to)
    return sessions.order_by("date", "start_time")


def attendance_percentage(present: int, total: int) -> float:
    return round((present / total) * 100, 1) if total else 0.0


class AttendanceMatrix(NamedTuple):
    sessions: list
    rows: list


def build_attendance_matrix(section: str = "", date_from=None, date_to=None) -> AttendanceMatrix:
    sessions = list(get_closed_sessions(date_from=date_from, date_to=date_to))
    students = (
        User.objects.filter(role=User.ROLE_STUDENT, student_profile__isnull=False)
        .select_related("student_profile")
        .order_by("student_profile__crn")
    )
    if section:
        students = students.filter(student_profile__section=section)
    present_pairs = set(
        Attendance.objects.filter(session__in=sessions).values_list("student_id", "session_id")
    )
    total = sum(s.periods for s in sessions)
    rows = []
    for student in students:
        presents = {s.id: (student.id, s.id) in present_pairs for s in sessions}
        # A merged double-period session (periods=2) counts as 2 towards both the
        # numerator and denominator — one QR scan, but it covers two timetable slots.
        present_count = sum(s.periods for s in sessions if presents[s.id])
        percentage = attendance_percentage(present_count, total)
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
    return AttendanceMatrix(sessions=sessions, rows=rows)


def sanitize_report_cell(value):
    """Prefix leading =+-@ with a quote so spreadsheet apps never parse a cell as a formula.

    CRN and name are free-text at student self-registration, so this is the export's
    only defense against CSV/formula injection (CWE-1236) into a teacher's report.
    """
    text = str(value)
    if text[:1] in ("=", "+", "-", "@"):
        return "'" + text
    return text


def build_report_rows(sessions, rows):
    header = (
        ["CRN", "Name"]
        + [f"{s.date.isoformat()} (x{s.periods})" if s.periods > 1 else s.date.isoformat() for s in sessions]
        + ["%"]
    )
    data_rows = [
        [sanitize_report_cell(r["crn"]), sanitize_report_cell(r["name"])]
        + ["P" if r["presents"][s.id] else "A" for s in sessions]
        + [r["percentage"]]
        for r in rows
    ]
    return header, data_rows
