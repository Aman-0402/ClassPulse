from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsTeacher, IsStudent
from attendance.models import AttendanceSession
from attendance.serializers import MarkAttendanceSerializer, QRTokenSerializer, SessionSerializer, StartSessionSerializer
from attendance.services import get_current_qr_token


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
        serializer = MarkAttendanceSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                attendance = serializer.save()
        except IntegrityError:
            return Response(
                {"detail": "Attendance already marked for this session."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"status": "marked", "marked_at": attendance.marked_at})
