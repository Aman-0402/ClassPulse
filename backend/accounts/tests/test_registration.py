from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from accounts.models import StudentProfile


class StudentRegistrationTest(APITestCase):
    def valid_payload(self, crn="22030145"):
        return {
            "username": "amanraj",
            "email": "aman@example.com",
            "password": "StrongPass123",
            "first_name": "Aman Raj",
            "crn": crn,
            "course": "B.Tech CSE",
            "semester": 5,
            "section": "A",
        }

    def test_register_creates_user_and_profile(self):
        url = reverse("student-register")
        response = self.client.post(url, self.valid_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(StudentProfile.objects.count(), 1)
        self.assertEqual(StudentProfile.objects.first().crn, "22030145")

    def test_duplicate_crn_rejected(self):
        url = reverse("student-register")
        self.client.post(url, self.valid_payload(crn="111"), format="json")
        response = self.client.post(
            url, self.valid_payload(crn="111") | {"username": "other"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("crn", response.data)
        self.assertEqual(StudentProfile.objects.count(), 1)
