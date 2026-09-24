from django.contrib import admin
from attendance.models import AttendanceSession, ClassSchedule, NotAttendingMark, QRToken, Attendance, ActivityLog


@admin.register(ClassSchedule)
class ClassScheduleAdmin(admin.ModelAdmin):
    list_display = ("day_of_week", "start_time", "end_time", "section", "subject")
    list_filter = ("day_of_week", "section")
    ordering = ("day_of_week", "start_time")


admin.site.register(AttendanceSession)
admin.site.register(QRToken)
admin.site.register(ActivityLog)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("student_name", "student_crn", "session", "session_section", "marked_at", "ip_address")
    list_filter = ("session__section", "session__date", "session__subject")
    search_fields = (
        "student__username",
        "student__first_name",
        "student__student_profile__crn",
        "student__student_profile__urn",
        "session__subject",
    )
    readonly_fields = ("marked_at",)
    ordering = ("-marked_at",)

    @admin.display(description="Student")
    def student_name(self, obj):
        return obj.student.get_full_name() or obj.student.username

    @admin.display(description="CRN")
    def student_crn(self, obj):
        profile = getattr(obj.student, "student_profile", None)
        return profile.crn if profile else "-"

    @admin.display(description="Section")
    def session_section(self, obj):
        return obj.session.section or "-"
admin.site.register(NotAttendingMark)
