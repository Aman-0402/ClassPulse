from rest_framework import serializers
from attendance.models import AttendanceSession, QRToken


class StartSessionSerializer(serializers.ModelSerializer):
    duration_minutes = serializers.IntegerField(required=False, min_value=1, max_value=180, default=5)
    closes_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = AttendanceSession
        fields = ["id", "subject", "date", "start_time", "duration_minutes", "closes_at", "status"]
        read_only_fields = ["id", "date", "start_time", "status"]

    def create(self, validated_data):
        return AttendanceSession.objects.create(teacher=self.context["request"].user, **validated_data)


class SessionSerializer(serializers.ModelSerializer):
    closes_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = AttendanceSession
        fields = ["id", "subject", "date", "start_time", "end_time", "duration_minutes", "closes_at", "status"]


class QRTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = QRToken
        fields = ["token", "expires_at"]


class TokenInputSerializer(serializers.Serializer):
    token = serializers.CharField()
