from django.urls import path

from tasks.views import StudentTaskListView, TeacherTaskDetailView, TeacherTaskListCreateView

urlpatterns = [
    path("teacher/", TeacherTaskListCreateView.as_view(), name="teacher-task-list"),
    path("teacher/<int:pk>/", TeacherTaskDetailView.as_view(), name="teacher-task-detail"),
    path("student/", StudentTaskListView.as_view(), name="student-task-list"),
]
