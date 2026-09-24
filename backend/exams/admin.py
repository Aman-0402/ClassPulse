from django.contrib import admin

from exams.models import MCQQuestion, PracticalQuestion


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
