from django.urls import path
from attendance.views import StartSessionView, StopSessionView

urlpatterns = [
    path("sessions/start/", StartSessionView.as_view(), name="session-start"),
    path("sessions/<int:session_id>/stop/", StopSessionView.as_view(), name="session-stop"),
]
