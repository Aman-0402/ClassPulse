from rest_framework import serializers
from attendance.models import AttendanceSession


class StartSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceSession
        fields = ["id", "subject", "date", "start_time", "status"]
        read_only_fields = ["id", "date", "start_time", "status"]

    def create(self, validated_data):
        return AttendanceSession.objects.create(teacher=self.context["request"].user, **validated_data)


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceSession
        fields = ["id", "subject", "date", "start_time", "end_time", "status"]
