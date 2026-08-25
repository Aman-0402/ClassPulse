from PIL import Image
from rest_framework import serializers
from accounts.models import ProfileEditRequest, StudentProfile

MAX_PHOTO_BYTES = 1 * 1024 * 1024


class StudentProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.first_name", read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            "id", "username", "email", "full_name",
            "crn", "urn", "course", "semester", "section", "photo",
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


class ProfilePhotoSerializer(serializers.Serializer):
    photo = serializers.ImageField()

    def validate_photo(self, value):
        if value.size > MAX_PHOTO_BYTES:
            raise serializers.ValidationError("Photo must be under 1MB.")
        try:
            image = Image.open(value)
            width, height = image.size
        except Exception:
            raise serializers.ValidationError("Could not read this image file.")
        if width != height:
            raise serializers.ValidationError(f"Photo must be square (got {width}x{height}).")
        value.seek(0)
        return value


class TeacherProfileSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    full_name = serializers.CharField(source="first_name")
    date_joined = serializers.DateTimeField()
