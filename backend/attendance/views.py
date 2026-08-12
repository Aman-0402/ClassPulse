import csv
from io import BytesIO

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from openpyxl import Workbook
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsTeacher, IsStudent
from attendance.exceptions import AttendanceError
from attendance.models import AttendanceSession, Attendance, ActivityLog
from attendance.serializers import QRTokenSerializer, SessionSerializer, StartSessionSerializer, TokenInputSerializer
from attendance.services import (
    attendance_percentage,
    build_attendance_matrix,
    build_report_rows,
    get_closed_sessions,
    get_current_qr_token,
    mark_attendance,
)


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
        percentage = attendance_percentage(present, total)
        return Response({"total": total, "present": present, "percentage": percentage, "history": history})


class AnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request):
        sessions, rows = build_attendance_matrix()
        total_sessions = len(sessions)
        total_students = len(rows)
        overall_present = sum(r["present_count"] for r in rows)
        overall_possible = total_students * total_sessions
        overall_rate = attendance_percentage(overall_present, overall_possible)
        students_data = [
            {
                "name": r["name"],
                "crn": r["crn"],
                "present": r["present_count"],
                "total": r["total"],
                "percentage": r["percentage"],
            }
            for r in rows
        ]
        below_threshold = [s for s in students_data if s["percentage"] < 75]
        return Response(
            {
                "total_sessions": total_sessions,
                "total_students": total_students,
                "overall_rate": overall_rate,
                "students": students_data,
                "below_threshold": below_threshold,
            }
        )


class ExportCSVView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request):
        sessions, rows = build_attendance_matrix()
        header, data_rows = build_report_rows(sessions, rows)
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=attendance_report.csv"
        response.write("﻿")  # UTF-8 BOM so Excel renders non-ASCII names correctly
        writer = csv.writer(response)
        writer.writerow(header)
        writer.writerows(data_rows)
        return response


class ExportExcelView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request):
        sessions, rows = build_attendance_matrix()
        header, data_rows = build_report_rows(sessions, rows)
        wb = Workbook()
        ws = wb.active
        ws.title = "Attendance"
        ws.append(header)
        for row in data_rows:
            ws.append(row)
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        response = HttpResponse(
            buffer.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = "attachment; filename=attendance_report.xlsx"
        return response
