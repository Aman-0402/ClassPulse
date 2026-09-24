from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsTeacher
from attendance.models import Attendance, AttendanceSession
from syllabus.models import SyllabusCompletion, SyllabusSession
from syllabus.serializers import MarkCompletionSerializer, SyllabusCompletionSerializer, SyllabusSessionSerializer


class SyllabusListView(generics.ListAPIView):
    """Read-only for everyone signed in — students and teachers both see the
    same course TOC, but the nested `completions` differ (see serializer)."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SyllabusSessionSerializer
    queryset = SyllabusSession.objects.prefetch_related("completions")
    pagination_class = None


class SyllabusManageListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]
    serializer_class = SyllabusSessionSerializer
    queryset = SyllabusSession.objects.prefetch_related("completions")
    pagination_class = None


class SyllabusManageDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]
    serializer_class = SyllabusSessionSerializer
    queryset = SyllabusSession.objects.prefetch_related("completions")


class AttendanceLookupView(APIView):
    """Given a section and date, the present count from that section's closed
    attendance session(s) that day — the auto-fill for the "mark complete"
    form. Returns null (not an error) when there's nothing to find, so the
    admin can still type the number in by hand."""

    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request):
        section = request.query_params.get("section", "").strip().upper()
        date = request.query_params.get("date", "")
        if not section or not date:
            return Response({"detail": "section and date are required."}, status=400)

        sessions = AttendanceSession.objects.filter(
            section=section, date=date, status=AttendanceSession.STATUS_CLOSED
        )
        if not sessions.exists():
            return Response({"present_count": None})
        present_count = Attendance.objects.filter(session__in=sessions).count()
        return Response({"present_count": present_count})


class MarkCompletionView(APIView):
    """POST marks (or updates) this session complete for one section; DELETE
    with the same body unmarks it. One record per (session, section) —
    marking again just overwrites the date/count rather than stacking up."""

    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def post(self, request, session_id):
        session = get_object_or_404(SyllabusSession, id=session_id)
        serializer = MarkCompletionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        completion, _ = SyllabusCompletion.objects.update_or_create(
            session=session,
            section=serializer.validated_data["section"],
            defaults={
                "date": serializer.validated_data["date"],
                "present_count": serializer.validated_data["present_count"],
                "marked_by": request.user,
            },
        )
        return Response(SyllabusCompletionSerializer(completion).data, status=status.HTTP_201_CREATED)

    def delete(self, request, session_id):
        section = request.query_params.get("section", "").strip().upper()
        if not section:
            return Response({"detail": "section is required."}, status=400)
        deleted, _ = SyllabusCompletion.objects.filter(session_id=session_id, section=section).delete()
        if not deleted:
            return Response({"detail": "No completion record for that section."}, status=404)
        return Response(status=status.HTTP_204_NO_CONTENT)
