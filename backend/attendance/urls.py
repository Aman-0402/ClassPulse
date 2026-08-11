from django.urls import path
from attendance.views import MarkAttendanceView, SessionLiveView, SessionQRView, StartSessionView, StopSessionView

urlpatterns = [
    path("sessions/start/", StartSessionView.as_view(), name="session-start"),
    path("sessions/<int:session_id>/stop/", StopSessionView.as_view(), name="session-stop"),
    path("sessions/<int:session_id>/qr/", SessionQRView.as_view(), name="session-qr"),
    path("sessions/<int:session_id>/live/", SessionLiveView.as_view(), name="session-live"),
    path("mark/", MarkAttendanceView.as_view(), name="attendance-mark"),
]
