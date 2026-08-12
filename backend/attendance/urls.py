from django.urls import path
from attendance.views import (
    AnalyticsView,
    MarkAttendanceView,
    SessionActivityView,
    SessionLiveView,
    SessionQRView,
    StartSessionView,
    StopSessionView,
    StudentHistoryView,
)

urlpatterns = [
    path("sessions/start/", StartSessionView.as_view(), name="session-start"),
    path("sessions/<int:session_id>/stop/", StopSessionView.as_view(), name="session-stop"),
    path("sessions/<int:session_id>/qr/", SessionQRView.as_view(), name="session-qr"),
    path("sessions/<int:session_id>/live/", SessionLiveView.as_view(), name="session-live"),
    path("sessions/<int:session_id>/activity/", SessionActivityView.as_view(), name="session-activity"),
    path("mark/", MarkAttendanceView.as_view(), name="attendance-mark"),
    path("student/history/", StudentHistoryView.as_view(), name="student-attendance-history"),
    path("analytics/", AnalyticsView.as_view(), name="attendance-analytics"),
]
