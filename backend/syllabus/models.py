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
