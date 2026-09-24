from django.urls import path

from syllabus.views import SyllabusListView, SyllabusManageDetailView, SyllabusManageListCreateView

urlpatterns = [
    path("", SyllabusListView.as_view(), name="syllabus-list"),
    path("manage/", SyllabusManageListCreateView.as_view(), name="syllabus-manage-list"),
    path("manage/<int:pk>/", SyllabusManageDetailView.as_view(), name="syllabus-manage-detail"),
]
