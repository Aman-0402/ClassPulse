import logging
from typing import NamedTuple

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import IntegrityError, transaction

from attendance.exceptions import (
    DuplicateAttendanceError,
    ExpiredTokenError,
    InvalidTokenError,
    SessionClosedError,
)
from accounts.models import User
from attendance.models import ActivityLog, AttendanceSession, QRToken, Attendance

logger = logging.getLogger(__name__)


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

    session = qr_token.session

    if session.status != AttendanceSession.STATUS_ACTIVE:
        log_activity(student, session, ActivityLog.TYPE_SESSION_CLOSED, ip_address, device_info)
        raise SessionClosedError()

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


def get_closed_sessions():
    return AttendanceSession.objects.filter(status=AttendanceSession.STATUS_CLOSED).order_by("date", "start_time")


class AttendanceMatrix(NamedTuple):
    sessions: list
    rows: list


def build_attendance_matrix() -> AttendanceMatrix:
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
    return AttendanceMatrix(sessions=sessions, rows=rows)
