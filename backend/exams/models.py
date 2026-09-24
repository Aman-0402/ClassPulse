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


class Exam(models.Model):
    """One exam scheduled for one section: a start/end window (auto open/close)
    plus a manual override, since the admin asked for both. Each student gets
    5 MCQs picked at random the first time they open it (see `ExamAttempt`) —
    the exam itself doesn't store which MCQs, only the one easy + one hard
    practical every student in the section sees.
    """

    STATUS_AUTO = "auto"
    STATUS_FORCED_OPEN = "forced_open"
    STATUS_FORCED_CLOSED = "forced_closed"
    STATUS_CHOICES = [
        (STATUS_AUTO, "Follow the scheduled window"),
        (STATUS_FORCED_OPEN, "Force open now"),
        (STATUS_FORCED_CLOSED, "Force closed now"),
    ]

    MCQ_COUNT = 5

    title = models.CharField(max_length=200, default="Exam")
    section = models.CharField(max_length=10)
    easy_practical = models.ForeignKey(
        PracticalQuestion, on_delete=models.PROTECT, related_name="exams_as_easy"
    )
    hard_practical = models.ForeignKey(
        PracticalQuestion, on_delete=models.PROTECT, related_name="exams_as_hard"
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    manual_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_AUTO)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_exams"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_time"]

    def __str__(self):
        return f"{self.title} — Section {self.section}"

    def is_open(self, now=None):
        if self.manual_status == self.STATUS_FORCED_OPEN:
            return True
        if self.manual_status == self.STATUS_FORCED_CLOSED:
            return False
        from django.utils import timezone

        now = now or timezone.now()
        return self.start_time <= now <= self.end_time


class ExamAttempt(models.Model):
    """A student's one attempt at an exam. `mcq_ids` is the fixed set of 5
    question ids assigned the first time they opened it - resumable, not
    re-randomized on reload. `answers` maps question id (string key, JSON
    requires that) to the chosen option letter.
    """

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="attempts")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="exam_attempts")
    mcq_ids = models.JSONField(default=list)
    answers = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["exam", "student"], name="one_attempt_per_student_per_exam"),
        ]

    def __str__(self):
        return f"{self.student} - {self.exam}"
