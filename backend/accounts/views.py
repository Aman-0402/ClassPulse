from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.permissions import IsStudent
from accounts.serializers import (
    ForgotPasswordSerializer,
    ProfileEditRequestCreateSerializer,
    ProfileEditRequestSerializer,
    ProfilePhotoSerializer,
    ResetPasswordSerializer,
    StudentProfileSerializer,
    TeacherProfileSerializer,
)
from accounts.models import PasswordResetOTP, ProfileEditRequest, StudentProfile


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
        return Response(StudentProfileSerializer(profile, context={"request": request}).data)


class ProfileEditRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def get(self, request):
        requests = ProfileEditRequest.objects.filter(student=request.user)[:10]
        return Response(ProfileEditRequestSerializer(requests, many=True).data)

    def post(self, request):
        if ProfileEditRequest.objects.filter(student=request.user, status=ProfileEditRequest.STATUS_PENDING).exists():
            return Response(
                {"detail": "You already have a pending edit request. Wait for it to be reviewed."}, status=400
            )
        serializer = ProfileEditRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        edit_request = serializer.save(student=request.user)
        return Response(ProfileEditRequestSerializer(edit_request).data, status=201)


class UpdateEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class UpdateEmailView(APIView):
    # Role-agnostic on purpose — both students and teachers use this (via
    # separate URLs, /api/student/email/ and /api/teacher/email/, but the
    # same view) since updating your own email isn't an identity-fraud risk
    # the way name/CRN/roll number are, for either role.
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = UpdateEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.email = serializer.validated_data["email"]
        request.user.save(update_fields=["email"])

        if request.user.role == request.user.ROLE_STUDENT:
            profile = get_object_or_404(StudentProfile.objects.select_related("user"), user=request.user)
            return Response(StudentProfileSerializer(profile, context={"request": request}).data)
        return Response(TeacherProfileSerializer(request.user).data)


class UpdateContactNumberSerializer(serializers.Serializer):
    contact_number = serializers.CharField(max_length=20)

    def validate_contact_number(self, value):
        digits_only = value.strip().lstrip("+")
        if not digits_only.isdigit() or not (7 <= len(digits_only) <= 15):
            raise serializers.ValidationError("Enter a valid phone number.")
        return value.strip()


class UpdateContactNumberView(APIView):
    # Student-only and direct self-service, same reasoning as UpdateEmailView —
    # a phone number typo isn't an identity-fraud/QR-attribution risk, so it
    # doesn't need the ProfileEditRequest admin-approval flow that name/CRN/
    # roll number go through.
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def post(self, request):
        serializer = UpdateContactNumberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = get_object_or_404(StudentProfile.objects.select_related("user"), user=request.user)
        profile.contact_number = serializer.validated_data["contact_number"]
        profile.save(update_fields=["contact_number"])
        return Response(StudentProfileSerializer(profile, context={"request": request}).data)


class ProfilePhotoView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def post(self, request):
        profile = get_object_or_404(StudentProfile, user=request.user)
        serializer = ProfilePhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile.photo = serializer.validated_data["photo"]
        profile.save(update_fields=["photo"])
        return Response(StudentProfileSerializer(profile, context={"request": request}).data)


class TeacherProfileView(APIView):
    def get(self, request):
        return Response(TeacherProfileSerializer(request.user).data)


class ForgotPasswordView(APIView):
    # Pre-auth by nature — a student who forgot their password has no token.
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "forgot_password"

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.context.get("user")
        if user is not None:
            PasswordResetOTP.objects.create(user=user)
        # Always the same response regardless of whether the username matched —
        # otherwise this endpoint could be used to enumerate valid usernames.
        return Response(
            {"detail": "If that account exists, an OTP has been generated. Ask your admin for the code."}
        )


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "reset_password"

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        otp_record = serializer.validated_data["otp_record"]

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        otp_record.used_at = timezone.now()
        otp_record.save(update_fields=["used_at"])
        # A leaked old token shouldn't outlive a password reset any more than
        # it should outlive a self-service change-password (same reasoning).
        Token.objects.filter(user=user).delete()

        return Response({"detail": "Password reset successfully. You can now log in."})
