import csv
from io import BytesIO

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
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
    close_session_if_window_expired,
    get_available_sections,
    get_closed_sessions,
    get_current_qr_token,
    get_current_schedule_slot,
    get_today_schedule,
    mark_attendance,
    merge_consecutive_slots,
)


class StartSessionView(generics.CreateAPIView):
    serializer_class = StartSessionSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeacher]


class CurrentScheduleView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request):
        slot = get_current_schedule_slot()
        if slot is None:
            return Response({"matched": False})
        return Response(
            {
                "matched": True,
                "subject": slot.subject,
                "section": slot.section,
                "start_time": slot.start_time,
                "end_time": slot.end_time,
            }
        )


class TodayScheduleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        slots = get_today_schedule()
        return Response(
            {
                "day": timezone.localdate().strftime("%A"),
                "slots": merge_consecutive_slots(slots),
            }
        )


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
        session = close_session_if_window_expired(session)
        if session.status == AttendanceSession.STATUS_CLOSED:
            return Response({"detail": "The attendance window has closed."}, status=400)
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
        session = close_session_if_window_expired(session)
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
        return Response(
            {
                "present_count": present_count,
                "recent": recent,
                "status": session.status,
                "closes_at": session.closes_at,
            }
        )


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
        total = sum(s.periods for s in sessions)
        present = sum(s.periods for s in sessions if s.id in present_session_ids)
        percentage = attendance_percentage(present, total)
        return Response({"total": total, "present": present, "percentage": percentage, "history": history})


class AnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request):
        section = request.query_params.get("section", "")
        sessions, rows = build_attendance_matrix(section=section)
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
                "available_sections": get_available_sections(),
                "section": section,
            }
        )


class ExportCSVView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request):
        section = request.query_params.get("section", "")
        sessions, rows = build_attendance_matrix(section=section)
        header, data_rows = build_report_rows(sessions, rows)
        filename = f"attendance_report_{section}.csv" if section else "attendance_report.csv"
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename={filename}"
        response.write("﻿")  # UTF-8 BOM so Excel renders non-ASCII names correctly
        writer = csv.writer(response)
        writer.writerow(header)
        writer.writerows(data_rows)
        return response


class ExportExcelView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request):
        section = request.query_params.get("section", "")
        sessions, rows = build_attendance_matrix(section=section)
        header, data_rows = build_report_rows(sessions, rows)
        filename = f"attendance_report_{section}.xlsx" if section else "attendance_report.xlsx"
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
        response["Content-Disposition"] = f"attachment; filename={filename}"
        return response


def compute_pdf_column_widths(num_columns, usable_width):
    """Column widths for the export PDF's table, guaranteed to sum to <= usable_width.

    CRN and Name get fixed widths; every remaining column (one per session, plus %)
    shares whatever space is left, shrinking toward unreadable rather than ever pushing
    the table wider than the page can actually hold.
    """
    crn_width = 60
    name_width = 120
    remaining_columns = num_columns - 2
    other_width = max(usable_width - crn_width - name_width, 0) / remaining_columns
    return [crn_width, name_width] + [other_width] * remaining_columns


def _strip_pdf_display_prefix(value):
    """CSV/Excel's formula-injection quote-prefix is a spreadsheet-only convention;
    PDF isn't a spreadsheet, so drop the leading quote here rather than showing it."""
    text = str(value)
    if text.startswith("'"):
        return text[1:]
    return text


class ExportPDFView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request):
        section = request.query_params.get("section", "")
        sessions, rows = build_attendance_matrix(section=section)
        header, data_rows = build_report_rows(sessions, rows)
        buffer = BytesIO()
        page_width, _ = landscape(A4)
        usable_width = page_width - 144  # SimpleDocTemplate's default 72pt margin on each side
        col_widths = compute_pdf_column_widths(len(header), usable_width)

        pdf_header = [_strip_pdf_display_prefix(cell) for cell in header]
        pdf_rows = [[_strip_pdf_display_prefix(cell) for cell in row] for row in data_rows]
        data = [pdf_header] + pdf_rows

        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                ]
            )
        )
        doc.build([table])
        buffer.seek(0)
        filename = f"attendance_report_{section}.pdf" if section else "attendance_report.pdf"
        response = HttpResponse(buffer.read(), content_type="application/pdf")
        response["Content-Disposition"] = f"attachment; filename={filename}"
        return response
