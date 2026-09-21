from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import ProfileEditRequest, StudentProfile

User = get_user_model()


class EditRequestReviewTestBase(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.teacher_token = Token.objects.create(user=self.teacher)
        self.student = User.objects.create_user(
            username="25BBA015", password="25BBA015", role=User.ROLE_STUDENT, first_name="Old Name"
        )
        self.profile = StudentProfile.objects.create(
            user=self.student, crn="25BBA015", urn="OLDURN01", course="BBA", semester=3, section="A"
        )
        self.student_token = Token.objects.create(user=self.student)

    def as_teacher(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.teacher_token.key}")

    def as_student(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.student_token.key}")


class ReviewListTest(EditRequestReviewTestBase):
    def test_teacher_sees_request_with_current_values_for_diffing(self):
        ProfileEditRequest.objects.create(student=self.student, requested_name="New Name", requested_crn="25BBA999")
        self.as_teacher()
        response = self.client.get(reverse("edit-request-review-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = response.data[0]
        self.assertEqual(row["full_name"], "Old Name")
        self.assertEqual(row["current_crn"], "25BBA015")
        self.assertEqual(row["requested_name"], "New Name")
        self.assertEqual(row["requested_crn"], "25BBA999")
        self.assertEqual(row["section"], "A")
        self.assertEqual(row["status"], "pending")

    def test_pending_listed_before_resolved_even_if_older(self):
        old_pending = ProfileEditRequest.objects.create(student=self.student, requested_name="A")
        other = User.objects.create_user(username="25BBA016", password="x", role=User.ROLE_STUDENT)
        StudentProfile.objects.create(user=other, crn="25BBA016", urn="U2", course="BBA", semester=3, section="A")
        resolved = ProfileEditRequest.objects.create(
            student=other, requested_name="B", status=ProfileEditRequest.STATUS_REJECTED
        )
        self.as_teacher()
        ids = [row["id"] for row in self.client.get(reverse("edit-request-review-list")).data]
        self.assertEqual(ids, [old_pending.id, resolved.id])

    def test_student_cannot_list(self):
        self.as_student()
        self.assertEqual(self.client.get(reverse("edit-request-review-list")).status_code, 403)

    def test_unauthenticated_rejected(self):
        self.assertEqual(self.client.get(reverse("edit-request-review-list")).status_code, 401)


class ReviewApproveTest(EditRequestReviewTestBase):
    def test_approve_applies_changes_and_records_reviewer(self):
        req = ProfileEditRequest.objects.create(
            student=self.student, requested_name="New Name", requested_urn="NEWURN01"
        )
        self.as_teacher()
        response = self.client.post(reverse("edit-request-approve", args=[req.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "approved")
        self.assertEqual(response.data["reviewed_by_username"], "prof")
        self.student.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.student.first_name, "New Name")
        self.assertEqual(self.profile.urn, "NEWURN01")
        self.assertEqual(self.profile.crn, "25BBA015")  # not requested, untouched

    def test_approve_crn_syncs_username_and_default_password(self):
        req = ProfileEditRequest.objects.create(student=self.student, requested_crn="25BBA999")
        self.as_teacher()
        self.assertEqual(self.client.post(reverse("edit-request-approve", args=[req.id])).status_code, 200)
        self.student.refresh_from_db()
        self.assertEqual(self.student.username, "25BBA999")
        self.assertTrue(self.student.check_password("25BBA999"))

    def test_approve_crn_already_taken_is_a_400_and_changes_nothing(self):
        other = User.objects.create_user(username="25BBA020", password="x", role=User.ROLE_STUDENT)
        StudentProfile.objects.create(user=other, crn="25BBA020", urn="U3", course="BBA", semester=3, section="A")
        req = ProfileEditRequest.objects.create(
            student=self.student, requested_name="Renamed", requested_crn="25BBA020"
        )
        self.as_teacher()
        response = self.client.post(reverse("edit-request-approve", args=[req.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("25BBA020", response.data["detail"])
        req.refresh_from_db()
        self.student.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(req.status, ProfileEditRequest.STATUS_PENDING)
        self.assertEqual(self.student.first_name, "Old Name")  # nothing half-applied
        self.assertEqual(self.profile.crn, "25BBA015")

    def test_cannot_approve_twice(self):
        req = ProfileEditRequest.objects.create(student=self.student, requested_name="New Name")
        self.as_teacher()
        self.client.post(reverse("edit-request-approve", args=[req.id]))
        response = self.client.post(reverse("edit-request-approve", args=[req.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_cannot_approve_their_own_request(self):
        req = ProfileEditRequest.objects.create(student=self.student, requested_name="Hacked")
        self.as_student()
        self.assertEqual(self.client.post(reverse("edit-request-approve", args=[req.id])).status_code, 403)
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, "Old Name")

    def test_unknown_request_is_404(self):
        self.as_teacher()
        self.assertEqual(self.client.post(reverse("edit-request-approve", args=[9999])).status_code, 404)


class ReviewRejectTest(EditRequestReviewTestBase):
    def test_reject_marks_rejected_and_changes_nothing(self):
        req = ProfileEditRequest.objects.create(student=self.student, requested_name="New Name")
        self.as_teacher()
        response = self.client.post(reverse("edit-request-reject", args=[req.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "rejected")
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, "Old Name")

    def test_cannot_reject_an_approved_request(self):
        req = ProfileEditRequest.objects.create(student=self.student, requested_name="New Name")
        self.as_teacher()
        self.client.post(reverse("edit-request-approve", args=[req.id]))
        self.assertEqual(self.client.post(reverse("edit-request-reject", args=[req.id])).status_code, 400)

    def test_student_cannot_reject(self):
        req = ProfileEditRequest.objects.create(student=self.student, requested_name="New Name")
        self.as_student()
        self.assertEqual(self.client.post(reverse("edit-request-reject", args=[req.id])).status_code, 403)
