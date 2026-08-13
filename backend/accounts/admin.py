from django.contrib import admin
from accounts.models import User, StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("crn", "user", "get_full_name", "course", "semester", "section")
    list_filter = ("section", "course", "semester")
    search_fields = ("crn", "user__username", "user__first_name")
    ordering = ("section", "crn")

    @admin.display(description="Name")
    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


admin.site.register(User)
