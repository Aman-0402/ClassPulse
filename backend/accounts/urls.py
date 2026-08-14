from django.urls import path
from accounts.views import RoleAwareLoginView, StudentProfileView

urlpatterns = [
    path("login/", RoleAwareLoginView.as_view(), name="login"),
    path("profile/", StudentProfileView.as_view(), name="student-profile"),
]
