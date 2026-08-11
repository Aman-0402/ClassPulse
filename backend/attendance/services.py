from attendance.models import AttendanceSession, QRToken


def get_current_qr_token(session: AttendanceSession) -> QRToken:
    latest = session.qr_tokens.order_by("-created_at").first()
    if latest and not latest.is_expired():
        return latest
    return QRToken.objects.create(session=session)
