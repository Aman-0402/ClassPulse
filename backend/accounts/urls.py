from django.urls import path
from accounts.views import RegisterStudentView, RoleAwareLoginView

urlpatterns = [
    path("register/", RegisterStudentView.as_view(), name="student-register"),
    path("login/", RoleAwareLoginView.as_view(), name="login"),
]
