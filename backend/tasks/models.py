from django.conf import settings
from django.db import models


class Task(models.Model):
    """A view-only task/assignment posted by a teacher/admin to one section.

    No submission model on purpose (per spec) — students only ever read this,
    they don't check it off or hand in work here.
    """

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    section = models.CharField(max_length=10)
    due_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_tasks"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "-created_at"]
        indexes = [
            models.Index(fields=["section"], name="task_section_idx"),
        ]

    def __str__(self):
        return f"{self.title} (Section {self.section})"
