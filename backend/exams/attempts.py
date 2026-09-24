"""Student-facing exam-taking logic: assign 5 random MCQs on first open
(fixed after that, so reload/resume shows the same questions), record
answers, and score on submit. Kept separate from the admin CRUD in
views.py/serializers.py since the two audiences never share a serializer
(students must never see `correct_option`).
"""
import random

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsStudent, IsTeacher
from exams.models import Exam, ExamAttempt, MCQQuestion


class StudentMCQSerializer(serializers.ModelSerializer):
    """What a student sees for one of their assigned MCQs — never the answer."""

    class Meta:
        model = MCQQuestion
        fields = ["id", "text", "option_a", "option_b", "option_c", "option_d"]


def _student_section(user):
    profile = getattr(user, "student_profile", None)
    if profile is None or not profile.section:
        raise PermissionDenied("Your profile has no section assigned yet.")
    return profile.section


def _serialize_attempt(exam, attempt):
    mcqs_by_id = {q.id: q for q in MCQQuestion.objects.filter(id__in=attempt.mcq_ids)}
    ordered_mcqs = [mcqs_by_id[qid] for qid in attempt.mcq_ids if qid in mcqs_by_id]
    return {
        "exam_id": exam.id,
        "title": exam.title,
        "section": exam.section,
        "easy_practical_text": exam.easy_practical.text,
        "hard_practical_text": exam.hard_practical.text,
        "mcqs": StudentMCQSerializer(ordered_mcqs, many=True).data,
        "answers": attempt.answers,
        "submitted": attempt.submitted_at is not None,
        "score": attempt.score,
        "total": len(attempt.mcq_ids),
        "is_open": exam.is_open(),
    }


class StudentExamListView(APIView):
    """Every exam for the student's section, newest first, with their own
    attempt status (not_started / in_progress / submitted) so the portal can
    show a single list instead of the student having to guess exam ids."""

    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def get(self, request):
        section = _student_section(request.user)
        exams = Exam.objects.filter(section=section).select_related("easy_practical", "hard_practical")
        attempts = {a.exam_id: a for a in ExamAttempt.objects.filter(student=request.user, exam__in=exams)}
        results = []
        for exam in exams:
            attempt = attempts.get(exam.id)
            if attempt is None:
                status_label = "not_started"
            elif attempt.submitted_at is not None:
                status_label = "submitted"
            else:
                status_label = "in_progress"
            results.append(
                {
                    "id": exam.id,
                    "title": exam.title,
                    "section": exam.section,
                    "start_time": exam.start_time,
                    "end_time": exam.end_time,
                    "is_open": exam.is_open(),
                    "status": status_label,
                    "score": attempt.score if attempt else None,
                    "total": len(attempt.mcq_ids) if attempt else Exam.MCQ_COUNT,
                }
            )
        return Response(results)


class StudentExamAttemptView(APIView):
    """GET starts (assigns 5 random MCQs, once) or resumes the student's
    attempt at one exam. PATCH saves answers. Both refuse a section mismatch
    and a not-yet-open exam with no existing attempt."""

    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def _get_exam_and_attempt(self, request, exam_id, create=False):
        section = _student_section(request.user)
        exam = get_object_or_404(Exam, id=exam_id)
        if exam.section != section:
            raise PermissionDenied("This exam is not for your section.")
        attempt = ExamAttempt.objects.filter(exam=exam, student=request.user).first()
        if attempt is None:
            if not create:
                raise PermissionDenied("You haven't started this exam.")
            if not exam.is_open():
                raise PermissionDenied("This exam is not open right now.")
            pool = list(MCQQuestion.objects.filter(is_active=True).values_list("id", flat=True))
            chosen = random.sample(pool, k=min(Exam.MCQ_COUNT, len(pool)))
            attempt = ExamAttempt.objects.create(exam=exam, student=request.user, mcq_ids=chosen)
        return exam, attempt

    def get(self, request, exam_id):
        exam, attempt = self._get_exam_and_attempt(request, exam_id, create=True)
        return Response(_serialize_attempt(exam, attempt))

    def patch(self, request, exam_id):
        exam, attempt = self._get_exam_and_attempt(request, exam_id, create=False)
        if attempt.submitted_at is not None:
            return Response({"detail": "You've already submitted this exam."}, status=status.HTTP_400_BAD_REQUEST)
        if not exam.is_open():
            return Response({"detail": "The exam window has closed."}, status=status.HTTP_400_BAD_REQUEST)

        answers = request.data.get("answers")
        if not isinstance(answers, dict):
            return Response({"detail": "answers must be an object of {question_id: option}."}, status=400)

        valid_ids = {str(qid) for qid in attempt.mcq_ids}
        for question_id, option in answers.items():
            if str(question_id) not in valid_ids:
                return Response({"detail": f"Question {question_id} is not part of your attempt."}, status=400)
            if option not in MCQQuestion.CHOICE_LETTERS:
                return Response({"detail": f"'{option}' is not a valid option."}, status=400)

        attempt.answers = {**attempt.answers, **{str(k): v for k, v in answers.items()}}
        attempt.save(update_fields=["answers"])
        return Response(_serialize_attempt(exam, attempt))


class StudentExamSubmitView(APIView):
    """Scores and locks the attempt. Idempotent — resubmitting just returns
    the already-computed score rather than erroring, since a flaky connection
    retry shouldn't strand a student who did submit successfully."""

    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def post(self, request, exam_id):
        section = _student_section(request.user)
        exam = get_object_or_404(Exam, id=exam_id)
        if exam.section != section:
            raise PermissionDenied("This exam is not for your section.")
        attempt = ExamAttempt.objects.filter(exam=exam, student=request.user).first()
        if attempt is None:
            raise PermissionDenied("You haven't started this exam.")

        if attempt.submitted_at is None:
            correct_by_id = dict(
                MCQQuestion.objects.filter(id__in=attempt.mcq_ids).values_list("id", "correct_option")
            )
            score = sum(
                1
                for qid in attempt.mcq_ids
                if attempt.answers.get(str(qid)) == correct_by_id.get(qid)
            )
            attempt.score = score
            attempt.submitted_at = timezone.now()
            attempt.save(update_fields=["score", "submitted_at"])

        return Response(_serialize_attempt(exam, attempt))


class TeacherExamResultsView(APIView):
    """Per-student MCQ scores for one exam, plus the class average - the
    admin/teacher side of "see per-student results and class stats"."""

    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request, exam_id):
        exam = get_object_or_404(Exam, id=exam_id)
        attempts = ExamAttempt.objects.filter(exam=exam).select_related("student", "student__student_profile")
        students = []
        for attempt in attempts:
            profile = getattr(attempt.student, "student_profile", None)
            students.append(
                {
                    "crn": profile.crn if profile else "",
                    "name": attempt.student.get_full_name() or attempt.student.username,
                    "status": "submitted" if attempt.submitted_at else "in_progress",
                    "score": attempt.score,
                    "total": len(attempt.mcq_ids),
                    "submitted_at": attempt.submitted_at,
                }
            )
        students.sort(key=lambda s: s["crn"])
        submitted_scores = [s["score"] for s in students if s["score"] is not None]
        average_score = round(sum(submitted_scores) / len(submitted_scores), 1) if submitted_scores else None
        return Response(
            {
                "exam_id": exam.id,
                "title": exam.title,
                "section": exam.section,
                "attempted": len(students),
                "submitted": len(submitted_scores),
                "average_score": average_score,
                "students": students,
            }
        )
