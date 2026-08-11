import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

QR_TOKEN_LIFETIME_SECONDS = 15


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
    date = models.DateField(default=timezone.localdate)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} ({self.date})"


def default_qr_expiry():
    return timezone.now() + timezone.timedelta(seconds=QR_TOKEN_LIFETIME_SECONDS)


class QRToken(models.Model):
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name="qr_tokens")
    token = models.CharField(max_length=64, unique=True, default=generate_qr_token)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_qr_expiry)

    def is_expired(self):
        return timezone.now() >= self.expires_at

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

    def __str__(self):
        return f"{self.student} - {self.session} ({self.status})"
