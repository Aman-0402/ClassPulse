from django.urls import path
from accounts.views import (
    ProfileEditRequestView,
    ProfilePhotoView,
    RoleAwareLoginView,
    StudentProfileView,
)

urlpatterns = [
    path("login/", RoleAwareLoginView.as_view(), name="login"),
    path("profile/", StudentProfileView.as_view(), name="student-profile"),
    path("edit-request/", ProfileEditRequestView.as_view(), name="profile-edit-request"),
    path("photo/", ProfilePhotoView.as_view(), name="profile-photo"),
]
