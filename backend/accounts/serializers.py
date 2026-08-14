from rest_framework import serializers
from accounts.models import StudentProfile


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


class TeacherProfileSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    full_name = serializers.CharField(source="first_name")
    date_joined = serializers.DateTimeField()
