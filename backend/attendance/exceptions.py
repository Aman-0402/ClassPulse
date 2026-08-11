class AttendanceError(Exception):
    activity_type = "invalid_token"
    message = "Invalid QR code."


class InvalidTokenError(AttendanceError):
    activity_type = "invalid_token"
    message = "Invalid QR code."


class SessionClosedError(AttendanceError):
    activity_type = "session_closed"
    message = "This attendance session is closed."


class ExpiredTokenError(AttendanceError):
    activity_type = "expired_token"
    message = "QR code expired. Please scan the current QR code."


class DuplicateAttendanceError(AttendanceError):
    activity_type = "duplicate"
    message = "Attendance already marked for this session."
