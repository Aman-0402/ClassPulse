from rest_framework import serializers

from tasks.models import Task


class TaskSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id", "title", "description", "section", "due_date",
            "created_by_name", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by_name", "created_at", "updated_at"]

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return ""
        return obj.created_by.get_full_name() or obj.created_by.username

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Title is required.")
        return value

    def validate_section(self, value):
        value = value.strip().upper()
        if not value:
            raise serializers.ValidationError("Section is required.")
        return value
