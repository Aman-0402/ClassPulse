import io

from PIL import Image
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework import serializers
from accounts.models import PasswordResetOTP, ProfileEditRequest, StudentProfile

MAX_PHOTO_BYTES = 1 * 1024 * 1024


class StudentProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.first_name", read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            "id", "username", "email", "full_name",
            "crn", "urn", "course", "semester", "section", "contact_number", "photo",
        ]


class ProfileEditRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileEditRequest
        fields = ["requested_name", "requested_crn", "requested_urn", "reason"]

    def validate(self, attrs):
        if not (attrs.get("requested_name") or attrs.get("requested_crn") or attrs.get("requested_urn")):
            raise serializers.ValidationError("Request at least one of name, CRN, or roll number.")
        return attrs


class ProfileEditRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileEditRequest
        fields = [
            "id", "requested_name", "requested_crn", "requested_urn",
            "reason", "status", "created_at", "reviewed_at",
        ]


def _compress_to_jpeg(image: Image.Image, original_name: str) -> InMemoryUploadedFile:
    """Re-encode as JPEG, stepping quality (then dimensions, as a last resort)
    down until it fits under MAX_PHOTO_BYTES. The frontend's crop step already
    outputs a fixed 512x512 JPEG that's normally well under this, but this is
    the actual enforced limit for any upload, not just the guided crop path —
    so it compresses instead of just rejecting anything larger.
    """
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    buffer = io.BytesIO()
    for quality in (90, 80, 70, 60, 50, 40, 30):
        buffer.seek(0)
        buffer.truncate()
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
        if buffer.tell() <= MAX_PHOTO_BYTES:
            break

    while buffer.tell() > MAX_PHOTO_BYTES and min(image.size) > 128:
        image = image.resize((image.width * 3 // 4, image.height * 3 // 4))
        buffer.seek(0)
        buffer.truncate()
        image.save(buffer, format="JPEG", quality=60, optimize=True)

    buffer.seek(0)
    name = original_name.rsplit(".", 1)[0] + ".jpg"
    return InMemoryUploadedFile(buffer, None, name, "image/jpeg", buffer.getbuffer().nbytes, None)


class ProfilePhotoSerializer(serializers.Serializer):
    photo = serializers.ImageField()

    def validate_photo(self, value):
        try:
            image = Image.open(value)
            image.load()
        except Exception:
            raise serializers.ValidationError("Could not read this image file.")
        width, height = image.size
        if width != height:
            raise serializers.ValidationError(f"Photo must be square (got {width}x{height}).")

        if value.size <= MAX_PHOTO_BYTES:
            value.seek(0)
            return value

        compressed = _compress_to_jpeg(image, value.name or "photo.jpg")
        if compressed.size > MAX_PHOTO_BYTES:
            raise serializers.ValidationError("Could not compress this photo under 1MB. Try a smaller image.")
        return compressed


class TeacherProfileSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    full_name = serializers.CharField(source="first_name")
    date_joined = serializers.DateTimeField()
    pending_edit_requests_count = serializers.SerializerMethodField()

    def get_pending_edit_requests_count(self, obj):
        return ProfileEditRequest.objects.filter(status=ProfileEditRequest.STATUS_PENDING).count()


class ForgotPasswordSerializer(serializers.Serializer):
    username = serializers.CharField()

    def validate_username(self, value):
        User = get_user_model()
        try:
            user = User.objects.get(username=value, role=User.ROLE_STUDENT)
        except User.DoesNotExist:
            # Deliberately no distinct error — same generic response whether the
            # username exists or not, so this can't be used to enumerate accounts.
            return value
        self.context["user"] = user
        return value


class ResetPasswordSerializer(serializers.Serializer):
    username = serializers.CharField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        User = get_user_model()
        try:
            user = User.objects.get(username=attrs["username"], role=User.ROLE_STUDENT)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid username or OTP.")

        otp_record = (
            PasswordResetOTP.objects.filter(user=user, code=attrs["otp"]).order_by("-created_at").first()
        )
        if not otp_record or not otp_record.is_valid:
            raise serializers.ValidationError("Invalid or expired OTP. Request a new one.")

        try:
            validate_password(attrs["new_password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": exc.messages})

        attrs["user"] = user
        attrs["otp_record"] = otp_record
        return attrs


class PasswordResetOTPSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    full_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = PasswordResetOTP
        fields = ["id", "username", "full_name", "code", "created_at", "expires_at", "used_at", "status"]

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_status(self, obj):
        if obj.used_at:
            return "used"
        return "active" if obj.is_valid else "expired"
