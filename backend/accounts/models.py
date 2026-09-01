import random

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

OTP_VALIDITY_MINUTES = 10


class User(AbstractUser):
    ROLE_STUDENT = "student"
    ROLE_TEACHER = "teacher"
    ROLE_CHOICES = [
        (ROLE_STUDENT, "Student"),
        (ROLE_TEACHER, "Teacher"),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_STUDENT)


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    crn = models.CharField(max_length=30, unique=True)
    urn = models.CharField(max_length=30, blank=True, default="")
    course = models.CharField(max_length=100)
    semester = models.PositiveSmallIntegerField()
    section = models.CharField(max_length=10)
    contact_number = models.CharField(max_length=20, blank=True, default="")
    photo = models.ImageField(upload_to="student_photos/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.crn})"


class ProfileEditRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="profile_edit_requests")
    # Blank means "no change requested for this field" — a student can request
    # just one of name/CRN/roll number without having to resubmit the others.
    requested_name = models.CharField(max_length=150, blank=True, default="")
    requested_crn = models.CharField(max_length=30, blank=True, default="")
    requested_urn = models.CharField(max_length=30, blank=True, default="")
    reason = models.TextField(blank=True, default="")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_edit_requests"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student.get_full_name() or self.student.username} — {self.status}"


def _generate_otp_code():
    return f"{random.randint(0, 999999):06d}"


def _default_otp_expiry():
    return timezone.now() + timezone.timedelta(minutes=OTP_VALIDITY_MINUTES)


class PasswordResetOTP(models.Model):
    # There's no SMS/email service wired up for this app — the code is never
    # sent to the student directly. It's only ever visible here, in Django
    # admin, for the admin to read and relay to the student out-of-band (in
    # person or by phone) after confirming who they are.
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_otps")
    code = models.CharField(max_length=6, default=_generate_otp_code)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=_default_otp_expiry)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        # Django's default verbose name inserts a space before every capital
        # letter, which mangles an acronym like OTP into "Password reset o t
        # ps" in the admin sidebar — spelling it out keeps it findable.
        verbose_name = "Password Reset OTP"
        verbose_name_plural = "Password Reset OTPs"

    @property
    def is_valid(self):
        return self.used_at is None and timezone.now() < self.expires_at

    def __str__(self):
        return f"{self.user.username} — {self.code} ({'used' if self.used_at else 'active' if self.is_valid else 'expired'})"
