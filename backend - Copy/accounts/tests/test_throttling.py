from django.core.cache import cache
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

User = get_user_model()


class LoginThrottleTest(APITestCase):
    def setUp(self):
        cache.clear()
        User.objects.create_user(username="amanraj", password="StrongPass123", role=User.ROLE_STUDENT)

    def tearDown(self):
        cache.clear()

    def test_excess_login_attempts_throttled(self):
        url = reverse("login")
        for _ in range(10):
            response = self.client.post(url, {"username": "amanraj", "password": "wrong"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(url, {"username": "amanraj", "password": "wrong"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
