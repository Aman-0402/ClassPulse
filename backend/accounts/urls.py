from django.urls import path
from accounts.views import RegisterStudentView, RoleAwareLoginView, StudentProfileView

urlpatterns = [
    path("register/", RegisterStudentView.as_view(), name="student-register"),
    path("login/", RoleAwareLoginView.as_view(), name="login"),
    path("profile/", StudentProfileView.as_view(), name="student-profile"),
]
