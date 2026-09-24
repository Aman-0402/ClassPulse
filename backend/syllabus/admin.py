from django.contrib import admin

from syllabus.models import SyllabusCompletion, SyllabusSession


@admin.register(SyllabusSession)
class SyllabusSessionAdmin(admin.ModelAdmin):
    list_display = ["session_number", "topics"]
    ordering = ["session_number"]
    search_fields = ["topics"]


@admin.register(SyllabusCompletion)
class SyllabusCompletionAdmin(admin.ModelAdmin):
    list_display = ["session", "section", "date", "present_count", "marked_by"]
    list_filter = ["section"]
