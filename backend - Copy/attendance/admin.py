from django.contrib import admin
from attendance.models import AttendanceSession, ClassSchedule, QRToken, Attendance, ActivityLog


@admin.register(ClassSchedule)
class ClassScheduleAdmin(admin.ModelAdmin):
    list_display = ("day_of_week", "start_time", "end_time", "section", "subject")
    list_filter = ("day_of_week", "section")
    ordering = ("day_of_week", "start_time")


admin.site.register(AttendanceSession)
admin.site.register(QRToken)
admin.site.register(Attendance)
admin.site.register(ActivityLog)
