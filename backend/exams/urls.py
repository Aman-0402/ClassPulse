from django.urls import path

from exams.attempts import StudentExamAttemptView, StudentExamListView, StudentExamSubmitView, TeacherExamResultsView
from exams.views import (
    ExamDetailView,
    ExamListCreateView,
    MCQQuestionDetailView,
    MCQQuestionListCreateView,
    PracticalQuestionDetailView,
    PracticalQuestionListCreateView,
)

urlpatterns = [
    path("mcq/", MCQQuestionListCreateView.as_view(), name="mcq-list"),
    path("mcq/<int:pk>/", MCQQuestionDetailView.as_view(), name="mcq-detail"),
    path("practical/", PracticalQuestionListCreateView.as_view(), name="practical-list"),
    path("practical/<int:pk>/", PracticalQuestionDetailView.as_view(), name="practical-detail"),
    path("exam/", ExamListCreateView.as_view(), name="exam-list"),
    path("exam/<int:pk>/", ExamDetailView.as_view(), name="exam-detail"),
    path("exam/<int:exam_id>/results/", TeacherExamResultsView.as_view(), name="exam-results"),
    path("student/exams/", StudentExamListView.as_view(), name="student-exam-list"),
    path("student/exams/<int:exam_id>/", StudentExamAttemptView.as_view(), name="student-exam-attempt"),
    path("student/exams/<int:exam_id>/submit/", StudentExamSubmitView.as_view(), name="student-exam-submit"),
]
