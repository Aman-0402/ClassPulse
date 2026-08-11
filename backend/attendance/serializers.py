from rest_framework import serializers
from attendance.models import AttendanceSession, QRToken, Attendance


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


class QRTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = QRToken
        fields = ["token", "expires_at"]


class MarkAttendanceSerializer(serializers.Serializer):
    token = serializers.CharField()

    def validate_token(self, value):
        try:
            qr_token = QRToken.objects.select_related("session").get(token=value)
        except QRToken.DoesNotExist:
            raise serializers.ValidationError("Invalid QR code.")
        if qr_token.session.status != AttendanceSession.STATUS_ACTIVE:
            raise serializers.ValidationError("This attendance session is closed.")
        if qr_token.is_expired():
            raise serializers.ValidationError("QR code expired. Please scan the current QR code.")
        self._qr_token = qr_token
        return value

    def validate(self, attrs):
        request = self.context["request"]
        qr_token = self._qr_token
        if Attendance.objects.filter(student=request.user, session=qr_token.session).exists():
            raise serializers.ValidationError("Attendance already marked for this session.")
        attrs["session"] = qr_token.session
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        return Attendance.objects.create(
            student=request.user,
            session=validated_data["session"],
            ip_address=request.META.get("REMOTE_ADDR"),
            device_info=request.META.get("HTTP_USER_AGENT", "")[:255],
        )
