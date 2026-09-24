from rest_framework import serializers

from exams.models import MCQQuestion, PracticalQuestion


class MCQQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCQQuestion
        fields = [
            "id", "text", "option_a", "option_b", "option_c", "option_d",
            "correct_option", "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_text(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Question text is required.")
        return value

    def validate(self, attrs):
        for field in ["option_a", "option_b", "option_c", "option_d"]:
            value = attrs.get(field, getattr(self.instance, field, None))
            if not value or not str(value).strip():
                raise serializers.ValidationError({field: "This option cannot be blank."})
        return attrs


class PracticalQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PracticalQuestion
        fields = ["id", "text", "difficulty", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_text(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Question text is required.")
        return value
