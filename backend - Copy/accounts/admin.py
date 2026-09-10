from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from accounts.models import PasswordResetOTP, ProfileEditRequest, User, StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    # The full-detail lookup an admin needs — "who is this student" — since
    # there's no separate student-directory page in the app itself; this is
    # the one place contact number, email, and photo are all visible together.
    list_display = (
        "crn", "urn", "user", "get_full_name", "course", "semester", "section",
        "contact_number", "get_email",
    )
    list_filter = ("section", "course", "semester")
    search_fields = ("crn", "urn", "user__username", "user__first_name", "contact_number", "user__email")
    ordering = ("section", "crn")
    readonly_fields = ("photo_preview", "created_at", "updated_at")
    fields = (
        "user", "crn", "urn", "course", "semester", "section",
        "contact_number", "photo", "photo_preview", "created_at", "updated_at",
    )

    @admin.display(description="Name")
    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description="Email")
    def get_email(self, obj):
        return obj.user.email

    @admin.display(description="Photo preview")
    def photo_preview(self, obj):
        if not obj.photo:
            return "No photo uploaded"
        return format_html('<img src="{}" style="max-height:150px;border-radius:8px;" />', obj.photo.url)


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
            user_update_fields = []
            if edit_request.requested_name:
                student.first_name = edit_request.requested_name
                user_update_fields.append("first_name")
            profile = getattr(student, "student_profile", None)
            if profile:
                update_fields = []
                if edit_request.requested_crn:
                    profile.crn = edit_request.requested_crn
                    update_fields.append("crn")
                    # The login scheme is username=password=CRN — a CRN
                    # correction that only touched StudentProfile.crn left
                    # username stale, so the student's own current CRN
                    # stopped being their real password (a genuine reported
                    # bug: "wrong password" for exactly the students whose
                    # CRN had been corrected here). Keep both in lockstep.
                    student.username = edit_request.requested_crn
                    student.set_password(edit_request.requested_crn)
                    user_update_fields += ["username", "password"]
                if edit_request.requested_urn:
                    profile.urn = edit_request.requested_urn
                    update_fields.append("urn")
                if update_fields:
                    profile.save(update_fields=update_fields)
            if user_update_fields:
                student.save(update_fields=user_update_fields)
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


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    # Read this to relay the code to the student who requested it — verify
    # who they are first (this is the whole point of routing it through a
    # human instead of auto-sending it).
    list_display = ("user", "code", "created_at", "expires_at", "status")
    list_filter = ("user",)
    search_fields = ("user__username", "user__first_name", "code")
    readonly_fields = ("user", "code", "created_at", "expires_at", "used_at")
    ordering = ("-created_at",)

    @admin.display(description="Status")
    def status(self, obj):
        if obj.used_at:
            return "Used"
        return "Active" if obj.is_valid else "Expired"

    def has_add_permission(self, request):
        return False


admin.site.register(User)
