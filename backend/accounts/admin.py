from django.contrib import admin
from django.utils import timezone
from accounts.models import ProfileEditRequest, User, StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("crn", "urn", "user", "get_full_name", "course", "semester", "section")
    list_filter = ("section", "course", "semester")
    search_fields = ("crn", "urn", "user__username", "user__first_name")
    ordering = ("section", "crn")

    @admin.display(description="Name")
    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


@admin.register(ProfileEditRequest)
class ProfileEditRequestAdmin(admin.ModelAdmin):
    list_display = (
        "student", "requested_name", "requested_crn", "requested_urn", "status", "created_at",
    )
    list_filter = ("status",)
    search_fields = ("student__username", "student__first_name", "requested_crn", "requested_urn")
    readonly_fields = ("student", "requested_name", "requested_crn", "requested_urn", "reason", "created_at")
    actions = ["approve_requests", "reject_requests"]

    @admin.action(description="Approve selected requests and apply the changes")
    def approve_requests(self, request, queryset):
        applied = 0
        for edit_request in queryset.filter(status=ProfileEditRequest.STATUS_PENDING):
            student = edit_request.student
            if edit_request.requested_name:
                student.first_name = edit_request.requested_name
                student.save(update_fields=["first_name"])
            profile = getattr(student, "student_profile", None)
            if profile:
                update_fields = []
                if edit_request.requested_crn:
                    profile.crn = edit_request.requested_crn
                    update_fields.append("crn")
                if edit_request.requested_urn:
                    profile.urn = edit_request.requested_urn
                    update_fields.append("urn")
                if update_fields:
                    profile.save(update_fields=update_fields)
            edit_request.status = ProfileEditRequest.STATUS_APPROVED
            edit_request.reviewed_at = timezone.now()
            edit_request.reviewed_by = request.user
            edit_request.save(update_fields=["status", "reviewed_at", "reviewed_by"])
            applied += 1
        self.message_user(request, f"Approved and applied {applied} request(s).")

    @admin.action(description="Reject selected requests")
    def reject_requests(self, request, queryset):
        updated = queryset.filter(status=ProfileEditRequest.STATUS_PENDING).update(
            status=ProfileEditRequest.STATUS_REJECTED, reviewed_at=timezone.now(), reviewed_by=request.user
        )
        self.message_user(request, f"Rejected {updated} request(s).")


admin.site.register(User)
