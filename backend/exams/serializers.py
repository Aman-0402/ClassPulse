from rest_framework import serializers

from exams.models import Exam, MCQQuestion, PracticalQuestion


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


class ExamSerializer(serializers.ModelSerializer):
    easy_practical_text = serializers.CharField(source="easy_practical.text", read_only=True)
    hard_practical_text = serializers.CharField(source="hard_practical.text", read_only=True)
    is_open = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = [
            "id", "title", "section", "easy_practical", "hard_practical",
            "easy_practical_text", "hard_practical_text",
            "start_time", "end_time", "manual_status", "is_open", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_is_open(self, obj):
        return obj.is_open()

    def validate_title(self, value):
        value = value.strip() or "Exam"
        return value

    def validate_section(self, value):
        value = value.strip().upper()
        if not value:
            raise serializers.ValidationError("Section is required.")
        return value

    def validate_easy_practical(self, value):
        if value.difficulty != "easy":
            raise serializers.ValidationError("That question is not tagged easy.")
        return value

    def validate_hard_practical(self, value):
        if value.difficulty != "hard":
            raise serializers.ValidationError("That question is not tagged hard.")
        return value

    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"end_time": "End time must be after the start time."})
        if self.instance is None:
            active_mcqs = MCQQuestion.objects.filter(is_active=True).count()
            if active_mcqs < Exam.MCQ_COUNT:
                raise serializers.ValidationError(
                    f"Need at least {Exam.MCQ_COUNT} active MCQs in the bank before scheduling an exam "
                    f"(there are {active_mcqs})."
                )
        return attrs
