from django.contrib import admin

from tasks.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "section", "due_date", "created_by", "created_at"]
    list_filter = ["section"]
    search_fields = ["title", "description"]
