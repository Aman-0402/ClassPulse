from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from attendance.models import AttendanceSession


class AttendanceConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.group_name = f"attendance_session_{self.session_id}"
        self.joined_group = False
        user = self.scope.get("user")

        if user is None or not user.is_authenticated or user.role != user.ROLE_TEACHER:
            await self.close(code=4403)
            return

        owns_session = await self.session_owned_by(user)
        if not owns_session:
            await self.close(code=4404)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        self.joined_group = True
        await self.accept()

    async def disconnect(self, close_code):
        if self.joined_group:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def attendance_update(self, event):
        await self.send_json(event["data"])

    async def activity_update(self, event):
        await self.send_json(event["data"])

    @database_sync_to_async
    def session_owned_by(self, user):
        return AttendanceSession.objects.filter(id=self.session_id, teacher=user).exists()
