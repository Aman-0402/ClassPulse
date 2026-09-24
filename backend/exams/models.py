from django.conf import settings
from django.db import models


class MCQQuestion(models.Model):
    """One multiple-choice question in the shared bank.

    `is_active=False` lets admin retire a bad/duplicate question without
    breaking any exam that already drew it into a student's assigned set —
    that student still sees the question they were given; only future exams
    stop drawing from retired ones.
    """

    text = models.TextField()
    option_a = models.CharField(max_length=500)
    option_b = models.CharField(max_length=500)
    option_c = models.CharField(max_length=500)
    option_d = models.CharField(max_length=500)
    CHOICE_LETTERS = ["a", "b", "c", "d"]
    correct_option = models.CharField(max_length=1, choices=[(c, c.upper()) for c in CHOICE_LETTERS])
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_mcqs"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.text[:60]

    def option(self, letter: str) -> str:
        return getattr(self, f"option_{letter}")


class PracticalQuestion(models.Model):
    """A practical question, tagged easy/hard, shown to the student but never
    answered in-app (per spec) - admin picks one easy + one hard per exam.
    """

    DIFFICULTY_EASY = "easy"
    DIFFICULTY_HARD = "hard"
    DIFFICULTY_CHOICES = [(DIFFICULTY_EASY, "Easy"), (DIFFICULTY_HARD, "Hard")]

    text = models.TextField()
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_practicals"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.difficulty}] {self.text[:50]}"
