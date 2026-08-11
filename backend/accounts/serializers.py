from django.contrib.auth import get_user_model
from rest_framework import serializers
from accounts.models import StudentProfile

User = get_user_model()


class StudentRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150)
    crn = serializers.CharField(max_length=30)
    course = serializers.CharField(max_length=100)
    semester = serializers.IntegerField(min_value=1, max_value=12)
    section = serializers.CharField(max_length=10)
    photo = serializers.ImageField(required=False, allow_null=True)

    def validate_crn(self, value):
        if StudentProfile.objects.filter(crn=value).exists():
            raise serializers.ValidationError("A student with this CRN is already registered.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value

    def create(self, validated_data):
        photo = validated_data.pop("photo", None)
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            role=User.ROLE_STUDENT,
        )
        profile = StudentProfile.objects.create(
            user=user,
            crn=validated_data["crn"],
            course=validated_data["course"],
            semester=validated_data["semester"],
            section=validated_data["section"],
            photo=photo,
        )
        return profile

    def to_representation(self, instance):
        # `instance` here is the created StudentProfile, not a plain field-mapped
        # object, so the default field-by-field representation (which expects
        # attributes like `username`/`password` directly on the instance) does
        # not apply. Build the response from the profile and its related user.
        return {
            "id": instance.id,
            "username": instance.user.username,
            "email": instance.user.email,
            "first_name": instance.user.first_name,
            "crn": instance.crn,
            "course": instance.course,
            "semester": instance.semester,
            "section": instance.section,
        }


class StudentProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.first_name", read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            "id", "username", "email", "full_name",
            "crn", "course", "semester", "section", "photo",
        ]
