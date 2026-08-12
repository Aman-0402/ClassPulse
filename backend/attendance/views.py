from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsTeacher, IsStudent
from attendance.exceptions import AttendanceError
from attendance.models import AttendanceSession, Attendance, ActivityLog
from attendance.serializers import QRTokenSerializer, SessionSerializer, StartSessionSerializer, TokenInputSerializer
from attendance.services import get_closed_sessions, get_current_qr_token, mark_attendance


class StartSessionView(generics.CreateAPIView):
    serializer_class = StartSessionSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeacher]


class StopSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def post(self, request, session_id):
        session = get_object_or_404(AttendanceSession, id=session_id, teacher=request.user)
        if session.status == AttendanceSession.STATUS_CLOSED:
            return Response({"detail": "Session already closed."}, status=400)
        session.status = AttendanceSession.STATUS_CLOSED
        session.end_time = timezone.now()
        session.save(update_fields=["status", "end_time"])
        return Response(SessionSerializer(session).data)


class SessionQRView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request, session_id):
        session = get_object_or_404(AttendanceSession, id=session_id, teacher=request.user)
        token = get_current_qr_token(session)
        return Response(QRTokenSerializer(token).data)


class MarkAttendanceView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def post(self, request):
        serializer = TokenInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            attendance = mark_attendance(
                student=request.user,
                token_value=serializer.validated_data["token"],
                ip_address=request.META.get("REMOTE_ADDR"),
                device_info=request.META.get("HTTP_USER_AGENT", "")[:255],
            )
        except AttendanceError as exc:
            return Response({"detail": exc.message}, status=400)
        return Response({"status": "marked", "marked_at": attendance.marked_at})


class SessionLiveView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request, session_id):
        session = get_object_or_404(AttendanceSession, id=session_id, teacher=request.user)
        records = (
            Attendance.objects.filter(session=session)
            .select_related("student", "student__student_profile")
            .order_by("-marked_at")[:10]
        )
        recent = [
            {
                "name": record.student.get_full_name() or record.student.username,
                "crn": getattr(getattr(record.student, "student_profile", None), "crn", ""),
                "marked_at": record.marked_at,
            }
            for record in records
        ]
        present_count = Attendance.objects.filter(session=session).count()
        return Response({"present_count": present_count, "recent": recent})


class SessionActivityView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request, session_id):
        session = get_object_or_404(AttendanceSession, id=session_id, teacher=request.user)
        logs = (
            ActivityLog.objects.filter(session=session)
            .exclude(activity_type=ActivityLog.TYPE_SUCCESS)
            .select_related("student")
            .order_by("-created_at", "-id")[:50]
        )
        data = [
            {
                "activity_type": log.activity_type,
                "student": log.student.get_full_name() or log.student.username,
                "created_at": log.created_at,
            }
            for log in logs
        ]
        return Response({"logs": data})


class StudentHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def get(self, request):
        sessions = get_closed_sessions()
        present_session_ids = set(
            Attendance.objects.filter(student=request.user, session__in=sessions).values_list(
                "session_id", flat=True
            )
        )
        history = [
            {
                "date": s.date,
                "subject": s.subject,
                "status": "present" if s.id in present_session_ids else "absent",
            }
            for s in sessions
        ]
        total = len(history)
        present = len(present_session_ids)
        percentage = round((present / total) * 100, 1) if total else 0.0
        return Response({"total": total, "present": present, "percentage": percentage, "history": history})
