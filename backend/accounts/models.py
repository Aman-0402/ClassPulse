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
    course = models.CharField(max_length=100)
    semester = models.PositiveSmallIntegerField()
    section = models.CharField(max_length=10)
    photo = models.ImageField(upload_to="student_photos/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.crn})"
