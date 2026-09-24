from django.conf import settings
from django.db import models


class SyllabusSession(models.Model):
    """One row of the course TOC/syllabus: a session number and the topics
    covered — shown to both students and teachers, editable only by the
    admin/teacher. Seeded from the 48-session curriculum (see migration
    0002) but admin can add/edit/remove sessions as the course changes.
    """

    session_number = models.PositiveIntegerField(unique=True)
    topics = models.TextField()

    class Meta:
        ordering = ["session_number"]

    def __str__(self):
        return f"Session {self.session_number}: {self.topics[:50]}"


class SyllabusCompletion(models.Model):
    """Marks one syllabus session as taught for one section, on a given date,
    with how many students were present. Independent per section — the same
    session can be complete for Section A on one date and still pending for
    Section B. Marking again for the same (session, section) updates this
    record rather than creating a second one (see `update_or_create` in the
    view); unmarking deletes it.
    """

    session = models.ForeignKey(SyllabusSession, on_delete=models.CASCADE, related_name="completions")
    section = models.CharField(max_length=10)
    date = models.DateField()
    present_count = models.PositiveIntegerField()
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="marked_syllabus_completions"
    )
    marked_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["session", "section"], name="one_completion_per_session_section"),
        ]

    def __str__(self):
        return f"Session {self.session.session_number} — Section {self.section} ({self.date})"
