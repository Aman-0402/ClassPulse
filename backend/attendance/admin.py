from django.contrib import admin
from attendance.models import AttendanceSession, QRToken, Attendance, ActivityLog

admin.site.register(AttendanceSession)
admin.site.register(QRToken)
admin.site.register(Attendance)
admin.site.register(ActivityLog)
