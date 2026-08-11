from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from rest_framework.authtoken.models import Token
from attendance.ws_auth import TokenAuthMiddleware

User = get_user_model()


class TokenAuthMiddlewareTest(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.token = Token.objects.create(user=self.user)

    async def test_valid_token_sets_user(self):
        captured = {}

        async def dummy_app(scope, receive, send):
            captured["user"] = scope["user"]

        middleware = TokenAuthMiddleware(dummy_app)
        await middleware({"query_string": f"token={self.token.key}".encode(), "type": "websocket"}, None, None)
        self.assertEqual(captured["user"], self.user)

    async def test_missing_token_sets_anonymous(self):
        captured = {}

        async def dummy_app(scope, receive, send):
            captured["user"] = scope["user"]

        middleware = TokenAuthMiddleware(dummy_app)
        await middleware({"query_string": b"", "type": "websocket"}, None, None)
        self.assertTrue(captured["user"].is_anonymous)

    async def test_invalid_token_sets_anonymous(self):
        captured = {}

        async def dummy_app(scope, receive, send):
            captured["user"] = scope["user"]

        middleware = TokenAuthMiddleware(dummy_app)
        await middleware({"query_string": b"token=not-a-real-token", "type": "websocket"}, None, None)
        self.assertTrue(captured["user"].is_anonymous)

    async def test_inactive_user_token_sets_anonymous(self):
        self.user.is_active = False
        await database_sync_to_async(self.user.save)()

        captured = {}

        async def dummy_app(scope, receive, send):
            captured["user"] = scope["user"]

        middleware = TokenAuthMiddleware(dummy_app)
        await middleware({"query_string": f"token={self.token.key}".encode(), "type": "websocket"}, None, None)
        self.assertTrue(captured["user"].is_anonymous)
