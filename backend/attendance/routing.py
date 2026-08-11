from django.urls import path
from attendance.consumers import AttendanceConsumer

websocket_urlpatterns = [
    path("ws/attendance/<int:session_id>/", AttendanceConsumer.as_asgi()),
]
