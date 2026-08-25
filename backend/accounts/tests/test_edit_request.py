from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from accounts.models import ProfileEditRequest, StudentProfile

User = get_user_model()


class ProfileEditRequestTest(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="25BBA015", password="pw12345678", role=User.ROLE_STUDENT, first_name="Old Name"
        )
        self.profile = StudentProfile.objects.create(
            user=self.student, crn="25BBA015", urn="25262101758", course="BBA", semester=3, section="A"
        )
        self.token = Token.objects.create(user=self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_requires_at_least_one_field(self):
        response = self.client.post(reverse("profile-edit-request"), {"reason": "typo"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_request(self):
        response = self.client.post(
            reverse("profile-edit-request"),
            {"requested_name": "New Name", "reason": "Legal name change"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ProfileEditRequest.objects.count(), 1)
        self.assertEqual(response.data["status"], "pending")

    def test_cannot_submit_second_request_while_pending(self):
        self.client.post(reverse("profile-edit-request"), {"requested_name": "New Name"}, format="json")
        response = self.client.post(reverse("profile-edit-request"), {"requested_crn": "25BBA099"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ProfileEditRequest.objects.count(), 1)

    def test_can_submit_again_after_previous_reviewed(self):
        first = ProfileEditRequest.objects.create(
            student=self.student, requested_name="New Name", status=ProfileEditRequest.STATUS_APPROVED
        )
        response = self.client.post(reverse("profile-edit-request"), {"requested_crn": "25BBA099"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ProfileEditRequest.objects.count(), 2)

    def test_list_only_own_requests(self):
        other_student = User.objects.create_user(username="other", password="pw12345678", role=User.ROLE_STUDENT)
        ProfileEditRequest.objects.create(student=other_student, requested_name="Someone Else")
        ProfileEditRequest.objects.create(student=self.student, requested_name="Mine")
        response = self.client.get(reverse("profile-edit-request"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["requested_name"], "Mine")

    def test_teacher_cannot_access(self):
        teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        token = Token.objects.create(user=teacher)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.post(reverse("profile-edit-request"), {"requested_name": "X"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ProfileEditRequestApprovalTest(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="25BBA015", password="pw12345678", role=User.ROLE_STUDENT, first_name="Old Name"
        )
        self.profile = StudentProfile.objects.create(
            user=self.student, crn="25BBA015", urn="OLDURN01", course="BBA", semester=3, section="A"
        )

    def test_approving_applies_requested_changes(self):
        from accounts.admin import ProfileEditRequestAdmin
        from django.contrib.admin.sites import AdminSite

        edit_request = ProfileEditRequest.objects.create(
            student=self.student,
            requested_name="New Name",
            requested_urn="NEWURN01",
        )
        admin_instance = ProfileEditRequestAdmin(ProfileEditRequest, AdminSite())
        reviewer = User.objects.create_user(username="admin1", password="pw12345678", role=User.ROLE_TEACHER)

        class FakeMessages:
            def add(self, level, message, extra_tags):
                pass

        class FakeRequest:
            user = reviewer
            _messages = FakeMessages()

        admin_instance.approve_requests(FakeRequest(), ProfileEditRequest.objects.filter(id=edit_request.id))

        self.student.refresh_from_db()
        self.profile.refresh_from_db()
        edit_request.refresh_from_db()
        self.assertEqual(self.student.first_name, "New Name")
        self.assertEqual(self.profile.urn, "NEWURN01")
        self.assertEqual(self.profile.crn, "25BBA015")  # untouched — wasn't requested
        self.assertEqual(edit_request.status, ProfileEditRequest.STATUS_APPROVED)
        self.assertEqual(edit_request.reviewed_by, reviewer)
