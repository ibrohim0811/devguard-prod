import json
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model

User = get_user_model()


class ScanProgressConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        try:
            self.task_id = self.scope['url_route']['kwargs'].get('task_id')

            # 1. Query String parametridan token ajratish
            query_string = self.scope.get('query_string', b'').decode('utf-8')
            query_params = parse_qs(query_string)
            token_list = query_params.get('token', [])

            if not token_list:
                await self.close(code=4001)
                return

            raw_token = token_list[0]

            # 2. Token orqali foydalanuvchini aniqlash
            user = await self._get_user_from_token(raw_token)
            if not user or not user.is_authenticated:
                await self.close(code=4001)
                return

            # 3. Task egaligini tekshirish
            is_owner = await self._check_ownership(user, self.task_id)
            if not is_owner:
                await self.close(code=4003)
                return

            # 4. BIRINCHI NAVBATDA WebSocket-ni qabul qilamiz (Handshake muvaffaqiyatli tugashi uchun)
            await self.accept()

            # 5. KEYIN Redis channel layer guruhiga qo'shamiz
            self.room_group_name = f'scan_{self.task_id}'
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            user_identity = getattr(user, 'username', getattr(user, 'phone_number', getattr(user, 'email', str(user.pk))))
            print(f"✅ WS Success: User {user_identity} WebSocket-ga ulandi!")

        except Exception as e:
            print(f"❌ WS Connect Error: {e}")
            # Invalid close code 1011 o'rniga 4000 (Custom Error) beriladi
            await self.close(code=4000)

    async def receive(self, text_data=None, bytes_data=None):
        """Frontend tomondan kelgan ping/keep-alive xabarlarini qayta ishlash"""
        if text_data == "ping":
            await self.send(text_data="pong")

    @database_sync_to_async
    def _get_user_from_token(self, token_key):
        try:
            access_token = AccessToken(token_key)
            user_id = access_token['user_id']
            return User.objects.get(id=user_id)
        except Exception as e:
            print(f"❌ JWT Error: {e}")
            return None

    @database_sync_to_async
    def _check_ownership(self, user, task_id: str) -> bool:
        from users.models import ScanHistory
        return ScanHistory.objects.filter(task_id=task_id, webapp__user=user).exists()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            try:
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
            except Exception as e:
                print(f"⚠️ WS Disconnect Group Error: {e}")

    async def scan_status_update(self, event):
        message = event['message']
        await self.send(text_data=json.dumps(message))

        scan_status = message.get('status')
        if scan_status == 'completed':
            report = message.get('report', '')
            await self._save_report(self.task_id, report, 'completed')
        elif scan_status == 'failed':
            error_msg = message.get('message', 'Skanerlash muvaffaqiyatsiz tugadi.')
            await self._save_report(self.task_id, error_msg, 'failed')

    @database_sync_to_async
    def _save_report(self, task_id: str, report: str, status: str):
        try:
            from users.models import ScanHistory
            ScanHistory.objects.filter(task_id=task_id).update(
                result_summary=report
            )
        except Exception as e:
            print(f"❌ DB update error: {e}")