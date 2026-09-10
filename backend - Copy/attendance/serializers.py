from django.utils import timezone
from rest_framework import serializers
from attendance.models import AttendanceSession, QRToken


class StartSessionSerializer(serializers.ModelSerializer):
    duration_minutes = serializers.IntegerField(required=False, min_value=1, max_value=180, default=5)
    periods = serializers.IntegerField(required=False, min_value=1, max_value=2, default=1)
    closes_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = AttendanceSession
        fields = [
            "id",
            "subject",
            "section",
            "date",
            "start_time",
            "duration_minutes",
            "periods",
            "closes_at",
            "status",
        ]
        read_only_fields = ["id", "date", "start_time", "status"]

    def create(self, validated_data):
        teacher = self.context["request"].user
        section = validated_data.get("section", "")
        # A section-scoped session already existing today means this "start" is really
        # a re-start of the same class, not a second one — reactivate it instead of
        # creating a new row. Without this, stop-then-start-again same day produces two
        # separate AttendanceSession rows for one class, and build_attendance_matrix()
        # sums periods across every closed session — silently doubling both the
        # attendance total and, for anyone who only attended one of the two, their
        # numerator too (a real percentage-corruption bug, not just a display glitch).
        # Sessions started without a section (no timetable match) are exempt, same as
        # the wrong-section scan check elsewhere — nothing to dedupe against.
        if section:
            existing = (
                AttendanceSession.objects.filter(teacher=teacher, section=section, date=timezone.localdate())
                .order_by("-start_time")
                .first()
            )
            if existing:
                existing.status = AttendanceSession.STATUS_ACTIVE
                existing.start_time = timezone.now()
                existing.end_time = None
                existing.subject = validated_data.get("subject", existing.subject)
                existing.duration_minutes = validated_data.get("duration_minutes", existing.duration_minutes)
                existing.periods = validated_data.get("periods", existing.periods)
                existing.save(
                    update_fields=["status", "start_time", "end_time", "subject", "duration_minutes", "periods"]
                )
                return existing
        return AttendanceSession.objects.create(teacher=teacher, **validated_data)


class SessionSerializer(serializers.ModelSerializer):
    closes_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = AttendanceSession
        fields = [
            "id",
            "subject",
            "section",
            "date",
            "start_time",
            "end_time",
            "duration_minutes",
            "periods",
            "closes_at",
            "status",
        ]


class QRTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = QRToken
        fields = ["token", "expires_at"]


class TokenInputSerializer(serializers.Serializer):
    token = serializers.CharField()
