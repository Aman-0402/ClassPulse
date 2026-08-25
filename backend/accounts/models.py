from django.contrib.auth.models import AbstractUser
from django.db import models


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
