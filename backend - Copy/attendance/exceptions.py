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


class WrongSectionError(AttendanceError):
    activity_type = "wrong_section"

    def __init__(self, session_section):
        self.message = f"This QR code is for Section {session_section} only."
        super().__init__(self.message)
