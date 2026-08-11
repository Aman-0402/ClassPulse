from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from rest_framework.authtoken.models import Token
from attendance.models import AttendanceSession
from classpulse.asgi import application

User = get_user_model()


class AttendanceConsumerTest(TransactionTestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="prof", password="pw12345678", role=User.ROLE_TEACHER)
        self.other_teacher = User.objects.create_user(
            username="prof2", password="pw12345678", role=User.ROLE_TEACHER
        )
        self.student = User.objects.create_user(username="stud", password="pw12345678", role=User.ROLE_STUDENT)
        self.teacher_token = Token.objects.create(user=self.teacher)
        self.other_teacher_token = Token.objects.create(user=self.other_teacher)
        self.student_token = Token.objects.create(user=self.student)
        self.session = AttendanceSession.objects.create(teacher=self.teacher, subject="AI")

    async def test_owning_teacher_can_connect(self):
        communicator = WebsocketCommunicator(
            application, f"/ws/attendance/{self.session.id}/?token={self.teacher_token.key}"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_other_teacher_rejected(self):
        communicator = WebsocketCommunicator(
            application, f"/ws/attendance/{self.session.id}/?token={self.other_teacher_token.key}"
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_student_rejected(self):
        communicator = WebsocketCommunicator(
            application, f"/ws/attendance/{self.session.id}/?token={self.student_token.key}"
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_receives_group_broadcast(self):
        from channels.layers import get_channel_layer

        communicator = WebsocketCommunicator(
            application, f"/ws/attendance/{self.session.id}/?token={self.teacher_token.key}"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f"attendance_session_{self.session.id}",
            {"type": "attendance.update", "data": {"name": "Aman Raj", "present_count": 1}},
        )
        message = await communicator.receive_json_from()
        self.assertEqual(message["name"], "Aman Raj")
        self.assertEqual(message["present_count"], 1)
        await communicator.disconnect()
