from django.urls import path

from syllabus.views import (
    AttendanceLookupView,
    MarkCompletionView,
    SyllabusListView,
    SyllabusManageDetailView,
    SyllabusManageListCreateView,
)

urlpatterns = [
    path("", SyllabusListView.as_view(), name="syllabus-list"),
    path("manage/", SyllabusManageListCreateView.as_view(), name="syllabus-manage-list"),
    path("manage/<int:pk>/", SyllabusManageDetailView.as_view(), name="syllabus-manage-detail"),
    path("attendance-lookup/", AttendanceLookupView.as_view(), name="syllabus-attendance-lookup"),
    path("manage/<int:session_id>/completion/", MarkCompletionView.as_view(), name="syllabus-mark-completion"),
]
