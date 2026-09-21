from django.contrib.auth.password_validation import validate_password
from django.db.models import Case, IntegerField, Value, When
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, serializers
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.permissions import IsStudent, IsTeacher
from accounts.serializers import (
    ForgotPasswordSerializer,
    PasswordResetOTPSerializer,
    ProfileEditRequestCreateSerializer,
    ProfileEditRequestReviewSerializer,
    ProfileEditRequestSerializer,
    ProfilePhotoSerializer,
    ResetPasswordSerializer,
    StudentProfileSerializer,
    TeacherProfileSerializer,
)
from accounts.services import EditRequestError, approve_edit_request, reject_edit_request
from accounts.models import PasswordResetOTP, ProfileEditRequest, StudentProfile, StudentScanPolicy, User
from attendance.models import Attendance
from attendance.services import get_available_sections


class RoleAwareLoginView(ObtainAuthToken):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @staticmethod
    def _forgive_default_password_typos(data):
        """Students whose password is still the default (their CRN) often fail
        to log in only because the phone keyboard capitalised/lowercased it or
        added a space. Match the username case-insensitively and, ONLY while the
        account is still on its default password, ignore case/space in the
        password. Any password the student chose themselves stays exact."""
        username = str(data.get("username", "")).strip()
        password = str(data.get("password", ""))
        if not username or not password:
            return data
        user = User.objects.filter(username__iexact=username, role=User.ROLE_STUDENT).first()
        if user is None:
            return data
        fixed = {"username": user.username, "password": password}
        if not user.check_password(password) and user.check_password(user.username):
            if password.strip().lower() == user.username.lower():
                fixed["password"] = user.username
        return fixed

    def post(self, request, *args, **kwargs):
        data = self._forgive_default_password_typos(request.data)
        serializer = self.serializer_class(data=data, context={"request": request})
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
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_new_password(self, value):
        if value != value.strip():
            raise serializers.ValidationError("Password cannot start or end with spaces.")
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


class OTPHistoryView(generics.ListAPIView):
    # Full history, not just pending/active ones — the point of this page is
    # an audit trail (who requested, when, was it used or did it expire
    # unused), not just "what's currently actionable".
    permission_classes = [permissions.IsAuthenticated, IsTeacher]
    serializer_class = PasswordResetOTPSerializer
    queryset = PasswordResetOTP.objects.select_related("user").all()


class TeacherStudentDataView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]

    def get(self, request):
        section = request.query_params.get("section", "")
        selected_crn = request.query_params.get("crn", "")
        sections = get_available_sections()
        policy = StudentScanPolicy.current()
        if not section and sections:
            section = sections[0]

        students_qs = (
            StudentProfile.objects.select_related("user")
            .filter(user__role=User.ROLE_STUDENT)
            .order_by("section", "crn")
        )
        if section:
            students_qs = students_qs.filter(section=section)

        students = [
            {
                "crn": profile.crn,
                "roll_number": profile.urn,
                "name": profile.user.get_full_name() or profile.user.username,
                "section": profile.section,
                "email": profile.user.email,
                "contact_number": profile.contact_number,
                "photo": request.build_absolute_uri(profile.photo.url) if profile.photo else None,
                "trusted_device_bound": bool(profile.trusted_device_hash),
                "trusted_device_bound_at": profile.trusted_device_bound_at,
                "scan_profile_complete": profile.is_scan_profile_complete,
                "missing_scan_profile_fields": profile.missing_scan_profile_fields,
            }
            for profile in students_qs
        ]

        selected = None
        if selected_crn:
            profile = get_object_or_404(
                StudentProfile.objects.select_related("user"),
                crn=selected_crn,
                user__role=User.ROLE_STUDENT,
            )
            records = (
                Attendance.objects.filter(student=profile.user)
                .select_related("session")
                .only(
                    "marked_at",
                    "ip_address",
                    "device_info",
                    "session__date",
                    "session__subject",
                    "session__section",
                )
                .order_by("-session__date", "-marked_at")
            )[:100]
            selected = {
                "crn": profile.crn,
                "roll_number": profile.urn,
                "name": profile.user.get_full_name() or profile.user.username,
                "username": profile.user.username,
                "section": profile.section,
                "course": profile.course,
                "semester": profile.semester,
                "email": profile.user.email,
                "contact_number": profile.contact_number,
                "photo": request.build_absolute_uri(profile.photo.url) if profile.photo else None,
                "trusted_device_bound": bool(profile.trusted_device_hash),
                "trusted_device_bound_at": profile.trusted_device_bound_at,
                "scan_profile_complete": profile.is_scan_profile_complete,
                "missing_scan_profile_fields": profile.missing_scan_profile_fields,
                "password_note": "Current password cannot be shown because it is stored as a secure hash.",
                "attendance": [
                    {
                        "date": record.session.date,
                        "subject": record.session.subject,
                        "section": record.session.section,
                        "marked_at": record.marked_at,
                        "ip_address": record.ip_address,
                        "device_info": record.device_info,
                    }
                    for record in records
                ],
            }

        return Response(
            {
                "sections": sections,
                "section": section,
                "profile_scan_lock_enabled": policy.require_complete_profile,
                "students": students,
                "selected_student": selected,
            }
        )

    def post(self, request):
        crn = request.data.get("crn")
        action = request.data.get("action")
        if action == "toggle_profile_scan_lock":
            enabled = request.data.get("enabled")
            if not isinstance(enabled, bool):
                return Response({"detail": "enabled must be true or false."}, status=400)
            policy = StudentScanPolicy.current()
            policy.require_complete_profile = enabled
            policy.save(update_fields=["require_complete_profile", "updated_at"])
            return Response({"profile_scan_lock_enabled": policy.require_complete_profile})

        if action not in ("reset_password_to_crn", "reset_trusted_device") or not crn:
            return Response({"detail": "crn and a valid action are required."}, status=400)

        profile = get_object_or_404(
            StudentProfile.objects.select_related("user"),
            crn=crn,
            user__role=User.ROLE_STUDENT,
        )
        if action == "reset_password_to_crn":
            profile.user.set_password(profile.crn)
            profile.user.save(update_fields=["password"])
            return Response({"detail": f"Password reset to CRN for {profile.crn}."})

        profile.trusted_device_hash = ""
        profile.trusted_device_bound_at = None
        profile.save(update_fields=["trusted_device_hash", "trusted_device_bound_at"])
        return Response({"detail": f"Trusted device reset for {profile.crn}."})


class EditRequestReviewListView(generics.ListAPIView):
    # Pending first (that's what needs action), then newest first — resolved
    # ones stay listed as the history of what was approved/rejected and by whom.
    permission_classes = [permissions.IsAuthenticated, IsTeacher]
    serializer_class = ProfileEditRequestReviewSerializer

    def get_queryset(self):
        return (
            ProfileEditRequest.objects.select_related("student", "student__student_profile", "reviewed_by")
            .annotate(
                pending_first=Case(
                    When(status=ProfileEditRequest.STATUS_PENDING, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            )
            .order_by("pending_first", "-created_at")
        )


class _EditRequestActionView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]
    action = None

    def post(self, request, pk):
        edit_request = get_object_or_404(
            ProfileEditRequest.objects.select_related("student", "student__student_profile"), pk=pk
        )
        try:
            self.action(edit_request, request.user)
        except EditRequestError as exc:
            return Response({"detail": str(exc)}, status=400)
        edit_request.refresh_from_db()
        return Response(ProfileEditRequestReviewSerializer(edit_request).data)


class EditRequestApproveView(_EditRequestActionView):
    action = staticmethod(approve_edit_request)


class EditRequestRejectView(_EditRequestActionView):
    action = staticmethod(reject_edit_request)
