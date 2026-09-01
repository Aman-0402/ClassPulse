from django.urls import path
from accounts.views import (
    ForgotPasswordView,
    ProfileEditRequestView,
    ProfilePhotoView,
    ResetPasswordView,
    RoleAwareLoginView,
    StudentProfileView,
    UpdateContactNumberView,
    UpdateEmailView,
)

urlpatterns = [
    path("login/", RoleAwareLoginView.as_view(), name="login"),
    path("profile/", StudentProfileView.as_view(), name="student-profile"),
    path("edit-request/", ProfileEditRequestView.as_view(), name="profile-edit-request"),
    path("photo/", ProfilePhotoView.as_view(), name="profile-photo"),
    path("email/", UpdateEmailView.as_view(), name="update-email"),
    path("contact-number/", UpdateContactNumberView.as_view(), name="update-contact-number"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
]
