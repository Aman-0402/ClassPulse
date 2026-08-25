from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.serializers import StudentProfileSerializer, TeacherProfileSerializer
from accounts.models import StudentProfile


class RoleAwareLoginView(ObtainAuthToken):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "role": user.role, "username": user.username})


class LogoutView(APIView):
    def post(self, request):
        # Actually revoke the token server-side — without this, a token issued at
        # login stays valid forever even after the client "logs out" (which was
        # previously just clearing localStorage), a real risk on shared/lab machines.
        Token.objects.filter(user=request.user).delete()
        return Response(status=204)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        try:
            validate_password(value, user=self.context["request"].user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value


class ChangePasswordView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "change_password"

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response({"old_password": "Current password is incorrect."}, status=400)

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        # Rotate the token so a leaked/guessed old password can't ride an
        # already-issued session past this point — the whole point of letting
        # a student change away from the predictable default password.
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)
        return Response({"token": token.key})


class StudentProfileView(APIView):
    def get(self, request):
        profile = get_object_or_404(StudentProfile.objects.select_related("user"), user=request.user)
        return Response(StudentProfileSerializer(profile).data)


class TeacherProfileView(APIView):
    def get(self, request):
        return Response(TeacherProfileSerializer(request.user).data)
