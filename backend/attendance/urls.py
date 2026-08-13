from django.urls import path
from attendance.views import (
    AnalyticsView,
    CurrentScheduleView,
    ExportCSVView,
    ExportExcelView,
    ExportPDFView,
    MarkAttendanceView,
    SessionActivityView,
    SessionLiveView,
    SessionQRView,
    StartSessionView,
    StopSessionView,
    StudentHistoryView,
    TodayScheduleView,
)

urlpatterns = [
    path("schedule/current/", CurrentScheduleView.as_view(), name="schedule-current"),
    path("schedule/today/", TodayScheduleView.as_view(), name="schedule-today"),
    path("sessions/start/", StartSessionView.as_view(), name="session-start"),
    path("sessions/<int:session_id>/stop/", StopSessionView.as_view(), name="session-stop"),
    path("sessions/<int:session_id>/qr/", SessionQRView.as_view(), name="session-qr"),
    path("sessions/<int:session_id>/live/", SessionLiveView.as_view(), name="session-live"),
    path("sessions/<int:session_id>/activity/", SessionActivityView.as_view(), name="session-activity"),
    path("mark/", MarkAttendanceView.as_view(), name="attendance-mark"),
    path("student/history/", StudentHistoryView.as_view(), name="student-attendance-history"),
    path("analytics/", AnalyticsView.as_view(), name="attendance-analytics"),
    path("export/csv/", ExportCSVView.as_view(), name="export-csv"),
    path("export/excel/", ExportExcelView.as_view(), name="export-excel"),
    path("export/pdf/", ExportPDFView.as_view(), name="export-pdf"),
]
