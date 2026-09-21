from rest_framework import generics, permissions, serializers

from accounts.permissions import IsTeacher
from attendance.models import ClassSchedule


class ClassScheduleSerializer(serializers.ModelSerializer):
    day_name = serializers.CharField(source="get_day_of_week_display", read_only=True)
    section = serializers.CharField(max_length=10)
    subject = serializers.CharField(max_length=100)

    class Meta:
        model = ClassSchedule
        fields = ["id", "day_of_week", "day_name", "start_time", "end_time", "section", "subject"]

    def validate_section(self, value):
        value = value.strip().upper()
        if not value:
            raise serializers.ValidationError("Section is required.")
        return value

    def validate_subject(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Subject is required.")
        return value

    def validate_day_of_week(self, value):
        if value not in range(7):
            raise serializers.ValidationError("Day must be 0 (Monday) to 6 (Sunday).")
        return value

    def validate(self, attrs):
        current = self.instance
        start = attrs.get("start_time", current.start_time if current else None)
        end = attrs.get("end_time", current.end_time if current else None)
        day = attrs.get("day_of_week", current.day_of_week if current else None)
        section = attrs.get("section", current.section if current else None)

        if start is not None and end is not None and end <= start:
            raise serializers.ValidationError({"end_time": "End time must be after the start time."})

        # A section can't be in two classes at once. Back-to-back (end == next start) is fine.
        clashes = ClassSchedule.objects.filter(
            day_of_week=day, section=section, start_time__lt=end, end_time__gt=start
        )
        if current:
            clashes = clashes.exclude(pk=current.pk)
        clash = clashes.first()
        if clash:
            raise serializers.ValidationError(
                {
                    "start_time": (
                        f"Overlaps {clash.subject} for Section {clash.section} "
                        f"({clash.start_time:%H:%M}-{clash.end_time:%H:%M})."
                    )
                }
            )
        return attrs


class TimetableListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]
    serializer_class = ClassScheduleSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = ClassSchedule.objects.all()
        section = self.request.query_params.get("section")
        if section:
            queryset = queryset.filter(section=section.strip().upper())
        return queryset.order_by("section", "day_of_week", "start_time")


class TimetableDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacher]
    serializer_class = ClassScheduleSerializer
    queryset = ClassSchedule.objects.all()
