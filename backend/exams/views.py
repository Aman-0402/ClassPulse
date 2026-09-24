from rest_framework import generics, permissions

from accounts.permissions import IsTeacher
from exams.models import MCQQuestion, PracticalQuestion
from exams.serializers import MCQQuestionSerializer, PracticalQuestionSerializer


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
