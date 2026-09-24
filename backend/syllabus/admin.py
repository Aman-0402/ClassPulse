from django.contrib import admin

from syllabus.models import SyllabusSession


@admin.register(SyllabusSession)
class SyllabusSessionAdmin(admin.ModelAdmin):
    list_display = ["session_number", "topics"]
    ordering = ["session_number"]
    search_fields = ["topics"]
