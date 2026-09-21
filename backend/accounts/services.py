from django.db import transaction
from django.utils import timezone

from accounts.models import ProfileEditRequest, StudentProfile, User


class EditRequestError(Exception):
    """A profile-correction request can't be approved/rejected as asked."""


def _require_pending(edit_request):
    if edit_request.status != ProfileEditRequest.STATUS_PENDING:
        raise EditRequestError("This request has already been reviewed.")


def approve_edit_request(edit_request, reviewer):
    """Apply the requested name/CRN/roll-number changes and mark it approved.

    Shared by the in-app review page and the Django admin action so the two
    can't drift apart.
    """
    _require_pending(edit_request)

    student = edit_request.student
    profile = getattr(student, "student_profile", None)
    new_crn = edit_request.requested_crn

    if new_crn and profile:
        taken = (
            StudentProfile.objects.filter(crn=new_crn).exclude(pk=profile.pk).exists()
            or User.objects.filter(username=new_crn).exclude(pk=student.pk).exists()
        )
        if taken:
            raise EditRequestError(f"CRN {new_crn} already belongs to another student.")

    with transaction.atomic():
        user_fields = []
        if edit_request.requested_name:
            student.first_name = edit_request.requested_name
            user_fields.append("first_name")

        if profile:
            profile_fields = []
            if new_crn:
                old_crn = profile.crn
                profile.crn = new_crn
                profile_fields.append("crn")
                # Login is username == CRN. Leaving username stale after a CRN
                # correction was a real bug (the student's own current CRN
                # stopped working), so keep them in lockstep.
                student.username = new_crn
                user_fields.append("username")
                # The default password is the CRN too — move it along, but only
                # if the student never picked their own; silently overwriting a
                # password they chose would lock them out of it.
                if student.check_password(old_crn):
                    student.set_password(new_crn)
                    user_fields.append("password")
            if edit_request.requested_urn:
                profile.urn = edit_request.requested_urn
                profile_fields.append("urn")
            if profile_fields:
                profile.save(update_fields=profile_fields)

        if user_fields:
            student.save(update_fields=user_fields)

        edit_request.status = ProfileEditRequest.STATUS_APPROVED
        edit_request.reviewed_at = timezone.now()
        edit_request.reviewed_by = reviewer
        edit_request.save(update_fields=["status", "reviewed_at", "reviewed_by"])


def reject_edit_request(edit_request, reviewer):
    _require_pending(edit_request)
    edit_request.status = ProfileEditRequest.STATUS_REJECTED
    edit_request.reviewed_at = timezone.now()
    edit_request.reviewed_by = reviewer
    edit_request.save(update_fields=["status", "reviewed_at", "reviewed_by"])
