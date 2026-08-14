from django.shortcuts import get_object_or_404
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response


class RoleAwareLoginView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "role": user.role, "username": user.username})


from rest_framework.views import APIView
from accounts.serializers import StudentProfileSerializer, TeacherProfileSerializer
from accounts.models import StudentProfile


class StudentProfileView(APIView):
    def get(self, request):
        profile = get_object_or_404(StudentProfile.objects.select_related("user"), user=request.user)
        return Response(StudentProfileSerializer(profile).data)


class TeacherProfileView(APIView):
    def get(self, request):
        return Response(TeacherProfileSerializer(request.user).data)
