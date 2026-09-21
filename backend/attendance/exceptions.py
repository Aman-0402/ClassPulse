from accounts.models import SCAN_PROFILE_FIELD_LABELS


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


class IncompleteProfileError(AttendanceError):
    activity_type = "invalid_token"

    def __init__(self, missing_keys):
        self.missing_keys = list(missing_keys)
        labels = [SCAN_PROFILE_FIELD_LABELS.get(key, key) for key in self.missing_keys]
        if not labels or self.missing_keys == ["profile"]:
            self.message = "Complete your profile before scanning attendance."
        else:
            # "a", "a and b", "a, b and c" - name exactly what's still missing,
            # so adding one field and scanning again names only the rest.
            joined = labels[0] if len(labels) == 1 else ", ".join(labels[:-1]) + " and " + labels[-1]
            self.message = f"Add your {joined} to mark attendance."
        super().__init__(self.message)
