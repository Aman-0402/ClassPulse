from django.contrib.auth import get_user_model
from rest_framework import serializers

from syllabus.models import SyllabusCompletion, SyllabusSession

User = get_user_model()


class SyllabusCompletionSerializer(serializers.ModelSerializer):
    marked_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SyllabusCompletion
        fields = ["id", "section", "date", "present_count", "marked_by_name", "marked_at"]

    def get_marked_by_name(self, obj):
        if not obj.marked_by:
            return ""
        return obj.marked_by.get_full_name() or obj.marked_by.username


class MarkCompletionSerializer(serializers.Serializer):
    section = serializers.CharField(max_length=10)
    date = serializers.DateField()
    present_count = serializers.IntegerField(min_value=0)

    def validate_section(self, value):
        value = value.strip().upper()
        if not value:
            raise serializers.ValidationError("Section is required.")
        return value


class SyllabusSessionSerializer(serializers.ModelSerializer):
    # Read-only view of who this session is done for: a student sees only
    # their own section's record (if any), a teacher sees every section's.
    completions = serializers.SerializerMethodField()

    class Meta:
        model = SyllabusSession
        fields = ["id", "session_number", "topics", "completions"]
        read_only_fields = ["id"]

    def validate_topics(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Topics text is required.")
        return value

    def get_completions(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        queryset = obj.completions.all()
        if user is not None and user.role == User.ROLE_STUDENT:
            profile = getattr(user, "student_profile", None)
            section = profile.section if profile else None
            queryset = queryset.filter(section=section) if section else queryset.none()
        return SyllabusCompletionSerializer(queryset, many=True).data
