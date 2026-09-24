from rest_framework import generics, permissions

from accounts.permissions import IsTeacher
from syllabus.models import SyllabusSession
from syllabus.serializers import SyllabusSessionSerializer


class SyllabusListView(generics.ListAPIView):
    """Read-only for everyone signed in — students and teachers both see the
    same course TOC."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SyllabusSessionSerializer
    queryset = SyllabusSession.objects.all()
    pagination_class = None


class SyllabusManageListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]
    serializer_class = SyllabusSessionSerializer
    queryset = SyllabusSession.objects.all()
    pagination_class = None


class SyllabusManageDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]
    serializer_class = SyllabusSessionSerializer
    queryset = SyllabusSession.objects.all()
