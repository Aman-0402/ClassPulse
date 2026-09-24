import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

QR_TOKEN_ROTATION_SECONDS = 15
QR_TOKEN_LIFETIME_SECONDS = 60


def generate_qr_token():
    return secrets.token_urlsafe(24)


class AttendanceSession(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_CLOSED, "Closed"),
    ]

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attendance_sessions"
    )
    subject = models.CharField(max_length=100)
    section = models.CharField(max_length=10, blank=True, default="")
    date = models.DateField(default=timezone.localdate)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveSmallIntegerField(default=5)
    periods = models.PositiveSmallIntegerField(
        default=1,
        help_text="Number of continuous timetable periods this single session covers (2 for a merged double period).",
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "date"], name="session_status_date_idx"),
            models.Index(fields=["section", "date"], name="session_section_date_idx"),
        ]

    def __str__(self):
        return f"{self.subject} ({self.date})"

    @property
    def closes_at(self):
        return self.start_time + timezone.timedelta(minutes=self.duration_minutes)

    def is_window_expired(self):
        return timezone.now() >= self.closes_at


def default_qr_expiry():
    return timezone.now() + timezone.timedelta(seconds=QR_TOKEN_LIFETIME_SECONDS)


class ClassSchedule(models.Model):
    MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY = range(7)
    DAY_CHOICES = [
        (MONDAY, "Monday"),
        (TUESDAY, "Tuesday"),
        (WEDNESDAY, "Wednesday"),
        (THURSDAY, "Thursday"),
        (FRIDAY, "Friday"),
        (SATURDAY, "Saturday"),
        (SUNDAY, "Sunday"),
    ]

    day_of_week = models.PositiveSmallIntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    section = models.CharField(max_length=10)
    subject = models.CharField(max_length=100, default="AI Training")

    class Meta:
        ordering = ["day_of_week", "start_time"]

    def __str__(self):
        return f"{self.get_day_of_week_display()} {self.start_time}-{self.end_time} BBA III {self.section}"


class QRToken(models.Model):
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name="qr_tokens")
    token = models.CharField(max_length=64, unique=True, default=generate_qr_token)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_qr_expiry)

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def should_rotate(self):
        return timezone.now() >= self.created_at + timezone.timedelta(seconds=QR_TOKEN_ROTATION_SECONDS)

    def __str__(self):
        return self.token


class Attendance(models.Model):
    STATUS_PRESENT = "present"
    STATUS_CHOICES = [(STATUS_PRESENT, "Present")]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attendance_records"
    )
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name="attendance_records")
    marked_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PRESENT)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "session"], name="unique_attendance_per_session"),
        ]
        indexes = [
            models.Index(fields=["session", "student"], name="attendance_session_student_idx"),
        ]

    def __str__(self):
        return f"{self.student} - {self.session} ({self.status})"


class ActivityLog(models.Model):
    TYPE_SUCCESS = "success"
    TYPE_DUPLICATE = "duplicate"
    TYPE_EXPIRED_TOKEN = "expired_token"
    TYPE_INVALID_TOKEN = "invalid_token"
    TYPE_SESSION_CLOSED = "session_closed"
    TYPE_NEW_DEVICE = "new_device"
    TYPE_WRONG_SECTION = "wrong_section"
    TYPE_CHOICES = [
        (TYPE_SUCCESS, "Success"),
        (TYPE_DUPLICATE, "Duplicate Attempt"),
        (TYPE_EXPIRED_TOKEN, "Expired QR"),
        (TYPE_INVALID_TOKEN, "Invalid QR"),
        (TYPE_SESSION_CLOSED, "Session Closed"),
        (TYPE_NEW_DEVICE, "New Device"),
        (TYPE_WRONG_SECTION, "Wrong Section"),
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activity_logs"
    )
    session = models.ForeignKey(
        AttendanceSession, on_delete=models.SET_NULL, related_name="activity_logs", null=True, blank=True
    )
    activity_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.student} ({self.created_at})"


class NotAttendingMark(models.Model):
    """A per-day flag: this student is known not to be attending class that
    day (dropped out temporarily, on leave, etc.) — visually distinct from a
    plain unexplained Absent on Day-wise Attendance, but counts exactly the
    same as absent everywhere attendance percentage is calculated (it's just
    the absence of an Attendance row, same as always — this model only
    records the label, it never creates or blocks an Attendance row).

    Scoped by date, not by a specific AttendanceSession, since a section can
    have more than one session in a day and this label applies to the whole
    day. If the student does scan in later that day, the real Attendance row
    takes precedence in `get_day_attendance` — this mark is simply ignored,
    not deleted, so re-marking is idempotent.
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="not_attending_marks"
    )
    section = models.CharField(max_length=10)
    date = models.DateField()
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="marked_not_attending"
    )
    marked_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "date"], name="one_not_attending_mark_per_student_per_day"),
        ]

    def __str__(self):
        return f"{self.student} not attending on {self.date}"
