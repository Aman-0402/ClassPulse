from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied

from accounts.permissions import IsStudent, IsTeacher
from tasks.models import Task
from tasks.serializers import TaskSerializer


class TeacherTaskListCreateView(generics.ListCreateAPIView):
    """Admin/teacher: list every task (optionally filtered by section), or post a new one."""

    permission_classes = [permissions.IsAuthenticated, IsTeacher]
    serializer_class = TaskSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = Task.objects.all()
        section = self.request.query_params.get("section")
        if section:
            queryset = queryset.filter(section=section.strip().upper())
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class TeacherTaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]
    serializer_class = TaskSerializer
    queryset = Task.objects.all()


class StudentTaskListView(generics.ListAPIView):
    """Student: read-only, only their own section's tasks."""

    permission_classes = [permissions.IsAuthenticated, IsStudent]
    serializer_class = TaskSerializer
    pagination_class = None

    def get_queryset(self):
        profile = getattr(self.request.user, "student_profile", None)
        if profile is None or not profile.section:
            raise PermissionDenied("Your profile has no section assigned yet.")
        return Task.objects.filter(section=profile.section)
