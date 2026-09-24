from rest_framework import serializers

from syllabus.models import SyllabusSession


class SyllabusSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyllabusSession
        fields = ["id", "session_number", "topics"]
        read_only_fields = ["id"]

    def validate_topics(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Topics text is required.")
        return value
