from django.urls import path

from exams.views import (
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
]
