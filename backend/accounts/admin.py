from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from accounts.models import PasswordResetOTP, ProfileEditRequest, StudentScanPolicy, User, StudentProfile
from attendance.models import Attendance


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    # The full-detail lookup an admin needs — "who is this student" — since
    # there's no separate student-directory page in the app itself; this is
    # the one place contact number, email, and photo are all visible together.
    list_display = (
        "get_full_name", "crn", "urn", "course", "semester", "section",
        "contact_number", "get_email",
    )
    list_display_links = ("get_full_name", "crn")
    list_filter = ("section", "course", "semester")
    search_fields = ("crn", "urn", "user__username", "user__first_name", "contact_number", "user__email")
    ordering = ("section", "crn")
    readonly_fields = (
        "get_full_name", "get_username", "get_email", "password_note",
        "trusted_device_status", "photo_preview", "attendance_history", "created_at", "updated_at",
    )
    fields = (
        "user", "get_username", "get_full_name", "get_email", "password_note",
        "crn", "urn", "course", "semester", "section",
        "contact_number", "trusted_device_status", "photo", "photo_preview", "attendance_history",
        "created_at", "updated_at",
    )
    actions = ["reset_passwords_to_crn", "reset_trusted_devices"]

    @admin.display(description="Name")
    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description="Username")
    def get_username(self, obj):
        return obj.user.username

    @admin.display(description="Email")
    def get_email(self, obj):
        return obj.user.email

    @admin.display(description="Password")
    def password_note(self, obj):
        return format_html(
            "Current password cannot be shown because Django stores only a secure one-way hash. "
            "Use the selected-student action <strong>Reset password to CRN</strong> if the student forgot it."
        )

    @admin.display(description="Trusted device")
    def trusted_device_status(self, obj):
        if not obj.trusted_device_hash:
            return "Not linked yet"
        bound_at = timezone.localtime(obj.trusted_device_bound_at).strftime("%Y-%m-%d %I:%M %p") if obj.trusted_device_bound_at else "unknown time"
        return f"Linked since {bound_at}"

    @admin.display(description="Photo preview")
    def photo_preview(self, obj):
        if not obj.photo:
            return "No photo uploaded"
        return format_html('<img src="{}" style="max-height:150px;border-radius:8px;" />', obj.photo.url)

    @admin.display(description="Attendance history")
    def attendance_history(self, obj):
        records = (
            Attendance.objects.filter(student=obj.user)
            .select_related("session")
            .order_by("-session__date", "-marked_at")[:100]
        )
        if not records:
            return "No attendance marked yet."

        rows = format_html_join(
            "",
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>",
            (
                (
                    record.session.date,
                    record.session.subject,
                    record.session.section or "-",
                    timezone.localtime(record.marked_at).strftime("%I:%M %p"),
                    record.ip_address or "-",
                    record.device_info or "-",
                )
                for record in records
            ),
        )
        return format_html(
            '<table style="width:100%;border-collapse:collapse;">'
            '<thead><tr><th style="text-align:left;">Date</th><th style="text-align:left;">Subject</th>'
            '<th style="text-align:left;">Section</th><th style="text-align:left;">Time</th>'
            '<th style="text-align:left;">IP</th><th style="text-align:left;">Device</th></tr></thead>'
            "<tbody>{}</tbody></table>",
            rows,
        )

    @admin.action(description="Reset selected student passwords to their CRN")
    def reset_passwords_to_crn(self, request, queryset):
        updated = 0
        for profile in queryset.select_related("user"):
            profile.user.set_password(profile.crn)
            profile.user.save(update_fields=["password"])
            updated += 1
        self.message_user(request, f"Reset {updated} student password(s) to their CRN.")

    @admin.action(description="Reset selected trusted devices")
    def reset_trusted_devices(self, request, queryset):
        updated = queryset.update(trusted_device_hash="", trusted_device_bound_at=None)
        self.message_user(request, f"Reset {updated} trusted device link(s).")


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


@admin.register(StudentScanPolicy)
class StudentScanPolicyAdmin(admin.ModelAdmin):
    list_display = ("id", "require_complete_profile", "updated_at")

    def has_add_permission(self, request):
        return not StudentScanPolicy.objects.exists()


admin.site.register(User)
