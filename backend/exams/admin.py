from django.contrib import admin

from exams.models import Exam, ExamAttempt, MCQQuestion, PracticalQuestion


@admin.register(MCQQuestion)
class MCQQuestionAdmin(admin.ModelAdmin):
    list_display = ["text", "correct_option", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["text"]


@admin.register(PracticalQuestion)
class PracticalQuestionAdmin(admin.ModelAdmin):
    list_display = ["text", "difficulty", "is_active", "created_at"]
    list_filter = ["difficulty", "is_active"]
    search_fields = ["text"]


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ["title", "section", "start_time", "end_time", "manual_status", "created_at"]
    list_filter = ["section", "manual_status"]


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ["student", "exam", "score", "submitted_at"]
    list_filter = ["exam"]
