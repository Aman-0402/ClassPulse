"""
URL configuration for classpulse project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import re

from django.conf import settings
from django.contrib import admin
from django.urls import path, re_path, include
from django.views.static import serve as serve_static
from accounts.views import (
    ChangePasswordView,
    LogoutView,
    OTPHistoryView,
    TeacherProfileView,
    UpdateEmailView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/student/', include('accounts.urls')),
    path('api/teacher/profile/', TeacherProfileView.as_view(), name='teacher-profile'),
    path('api/teacher/email/', UpdateEmailView.as_view(), name='teacher-update-email'),
    path('api/teacher/otp-history/', OTPHistoryView.as_view(), name='otp-history'),
    path('api/logout/', LogoutView.as_view(), name='logout'),
    path('api/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('api/attendance/', include('attendance.urls')),
]

# Always serve media (student photos) through Django, not just in DEBUG — this
# app has no separate media server/CDN, and shared cPanel hosting has no other
# way to expose files outside the app's own docroot at a stable URL.
#
# Deliberately NOT using django.conf.urls.static.static() here — that helper
# has its own internal `if not settings.DEBUG: return []` guard baked in, so
# it silently registers no URL pattern at all in production regardless of how
# it's called. That was a real bug: routing correctly reached Django (after
# the passenger_wsgi.py /api fix), but Django itself had nothing to serve it
# with, so every photo 404'd. Calling django.views.static.serve directly
# bypasses that guard.
urlpatterns += [
    re_path(
        r"^%s(?P<path>.*)$" % re.escape(settings.MEDIA_URL.lstrip("/")),
        serve_static,
        {"document_root": settings.MEDIA_ROOT},
    ),
]
