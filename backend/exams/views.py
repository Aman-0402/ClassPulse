import csv
import io

from rest_framework import generics, permissions, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsTeacher
from exams.models import Exam, MCQQuestion, PracticalQuestion
from exams.serializers import ExamSerializer, MCQQuestionSerializer, PracticalQuestionSerializer

REQUIRED_MCQ_COLUMNS = ["text", "option_a", "option_b", "option_c", "option_d", "correct_option"]


class MCQQuestionListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]
    serializer_class = MCQQuestionSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = MCQQuestion.objects.all()
        active = self.request.query_params.get("active")
        if active is not None:
            queryset = queryset.filter(is_active=active.lower() in ("1", "true", "yes"))
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class MCQQuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]
    serializer_class = MCQQuestionSerializer
    queryset = MCQQuestion.objects.all()


class PracticalQuestionListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]
    serializer_class = PracticalQuestionSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = PracticalQuestion.objects.all()
        difficulty = self.request.query_params.get("difficulty")
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        active = self.request.query_params.get("active")
        if active is not None:
            queryset = queryset.filter(is_active=active.lower() in ("1", "true", "yes"))
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class PracticalQuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]
    serializer_class = PracticalQuestionSerializer
    queryset = PracticalQuestion.objects.all()


class ExamListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]
    serializer_class = ExamSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = Exam.objects.select_related("easy_practical", "hard_practical")
        section = self.request.query_params.get("section")
        if section:
            queryset = queryset.filter(section=section.strip().upper())
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ExamDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]
    serializer_class = ExamSerializer
    queryset = Exam.objects.select_related("easy_practical", "hard_practical")


class MCQBulkUploadView(APIView):
    """Add many MCQs at once from a CSV file, so 100+ questions don't need to
    be typed one at a time through the modal.

    Expected header row (case-insensitive, any column order):
    text, option_a, option_b, option_c, option_d, correct_option
    `correct_option` must be a/b/c/d (case-insensitive).

    Every row is validated independently — good rows are created, bad rows
    are reported with their row number and reason, nothing rolls back a
    partial success just because one row further down is malformed.
    """

    permission_classes = [permissions.IsAuthenticated, IsTeacher]
    parser_classes = [MultiPartParser]

    def post(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"detail": "Attach a CSV file as 'file'."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            text = upload.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            return Response({"detail": "Could not read that file as UTF-8 text CSV."}, status=400)

        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None:
            return Response({"detail": "The CSV file is empty."}, status=400)

        header_map = {name.strip().lower(): name for name in reader.fieldnames}
        missing = [col for col in REQUIRED_MCQ_COLUMNS if col not in header_map]
        if missing:
            return Response(
                {"detail": f"Missing column(s): {', '.join(missing)}. Expected: {', '.join(REQUIRED_MCQ_COLUMNS)}."},
                status=400,
            )

        created = 0
        errors = []
        to_create = []
        for row_number, row in enumerate(reader, start=2):  # row 1 is the header
            values = {col: (row.get(header_map[col]) or "").strip() for col in REQUIRED_MCQ_COLUMNS}
            if not any(values.values()):
                continue  # a blank line — skip silently rather than reporting a fake error

            row_errors = [col.replace("_", " ") for col in REQUIRED_MCQ_COLUMNS if not values[col]]
            correct = values["correct_option"].lower()
            if not row_errors and correct not in MCQQuestion.CHOICE_LETTERS:
                errors.append(f"Row {row_number}: correct_option must be a/b/c/d, got '{values['correct_option']}'.")
                continue
            if row_errors:
                errors.append(f"Row {row_number}: missing {', '.join(row_errors)}.")
                continue

            to_create.append(
                MCQQuestion(
                    text=values["text"],
                    option_a=values["option_a"],
                    option_b=values["option_b"],
                    option_c=values["option_c"],
                    option_d=values["option_d"],
                    correct_option=correct,
                    created_by=request.user,
                )
            )

        if to_create:
            MCQQuestion.objects.bulk_create(to_create)
            created = len(to_create)

        return Response({"created": created, "errors": errors}, status=status.HTTP_201_CREATED)
