from attendance.models import AttendanceSession, QRToken, Attendance


def get_current_qr_token(session: AttendanceSession) -> QRToken:
    latest = session.qr_tokens.order_by("-created_at", "-id").first()
    if latest and not latest.is_expired():
        return latest
    return QRToken.objects.create(session=session)


from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_attendance_update(attendance):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    profile = getattr(attendance.student, "student_profile", None)
    present_count = Attendance.objects.filter(session=attendance.session).count()
    async_to_sync(channel_layer.group_send)(
        f"attendance_session_{attendance.session_id}",
        {
            "type": "attendance.update",
            "data": {
                "name": attendance.student.get_full_name() or attendance.student.username,
                "crn": profile.crn if profile else "",
                "marked_at": attendance.marked_at.isoformat(),
                "present_count": present_count,
            },
        },
    )
