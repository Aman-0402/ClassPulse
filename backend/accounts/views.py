from rest_framework import generics, permissions
from accounts.serializers import StudentRegistrationSerializer


class RegisterStudentView(generics.CreateAPIView):
    serializer_class = StudentRegistrationSerializer
    permission_classes = [permissions.AllowAny]
