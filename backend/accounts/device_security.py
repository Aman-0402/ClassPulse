import hashlib

from django.utils import timezone

from accounts.models import StudentProfile, User


def hash_device_id(device_id: str) -> str:
    return hashlib.sha256(device_id.encode("utf-8")).hexdigest()


def detect_or_bind_student_device(user: User, device_id: str) -> bool:
    """Bind the first scan device, then flag unusual device use without blocking.

    Returns True when the scan should be treated as suspicious for admin/teacher
    visibility. Attendance is still allowed; this is an audit signal only.
    """
    if user.role != User.ROLE_STUDENT or not device_id:
        return False

    try:
        profile = user.student_profile
    except StudentProfile.DoesNotExist:
        return False

    device_hash = hash_device_id(device_id)
    same_device_used_by_other_student = (
        StudentProfile.objects.exclude(user=user).filter(trusted_device_hash=device_hash).exists()
    )

    if not profile.trusted_device_hash:
        profile.trusted_device_hash = device_hash
        profile.trusted_device_bound_at = timezone.now()
        profile.save(update_fields=["trusted_device_hash", "trusted_device_bound_at"])
        return same_device_used_by_other_student

    if profile.trusted_device_hash != device_hash:
        return True

    return same_device_used_by_other_student
