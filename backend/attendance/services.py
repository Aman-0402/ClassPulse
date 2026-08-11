import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import IntegrityError, transaction

from attendance.exceptions import (
    DuplicateAttendanceError,
    ExpiredTokenError,
    InvalidTokenError,
    SessionClosedError,
)
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
    entry = ActivityLog.objects.create(
        student=student,
        session=session,
        activity_type=activity_type,
        ip_address=ip_address or None,
        device_info=device_info,
    )
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

    log_activity(student, session, ActivityLog.TYPE_SUCCESS, ip_address, device_info)
    broadcast_attendance_update(attendance)
    return attendance
