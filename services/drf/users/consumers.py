import json
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model

User = get_user_model()


class ScanProgressConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.task_id = self.scope['url_route']['kwargs'].get('task_id')

        # 1. Query String dan (?token=...) token-ni ajratib olamiz
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        query_params = parse_qs(query_string)
        token_list = query_params.get('token', [])

        if not token_list:
            print("⚠️ WS Error: Token uzatilmadi")
            await self.close(code=4001)
            return

        raw_token = token_list[0]

        # 2. Token orqali foydalanuvchini bazadan topamiz
        user = await self._get_user_from_token(raw_token)

        if not user or not user.is_authenticated:
            print("⚠️ WS Error: Token noto'g'ri yoki yaroqsiz")
            await self.close(code=4001)
            return

        # 3. Task egaligini tekshiramiz
        is_owner = await self._check_ownership(user, self.task_id)
        if not is_owner:
            print(f"⚠️ WS Error: Task ({self.task_id}) user ({user}) ga tegishli emas")
            await self.close(code=4003)
            return

        # 4. Ulanishni qabul qilamiz va guruhga qo'shamiz
        self.room_group_name = f'scan_{self.task_id}'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        print(f"✅ WS Success: User {user.username} WebSocket-ga ulandi!")

    @database_sync_to_async
    def _get_user_from_token(self, token_key):
        """JWT Access Tokendan User-ni aniqlash"""
        try:
            access_token = AccessToken(token_key)
            user_id = access_token['user_id']
            return User.objects.get(id=user_id)
        except Exception as e:
            print(f"❌ JWT Parsing Error: {e}")
            return None

    @database_sync_to_async
    def _check_ownership(self, user, task_id: str) -> bool:
        """ScanHistory va User mosligini tekshirish"""
        from users.models import ScanHistory
        return ScanHistory.objects.filter(task_id=task_id, webapp__user=user).exists()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def scan_status_update(self, event):
        """FastAPI dan kelgan xabarni front-endga yuboradi va DB ni yangilaydi"""
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
            updated_count = ScanHistory.objects.filter(task_id=task_id).update(
                result_summary=report
            )
            if updated_count == 0:
                print(f"⚠️ ScanHistory topilmadi: task_id={task_id}")
            else:
                print(f"✅ ScanHistory yangilandi: task_id={task_id}, status={status}")
        except Exception as e:
            print(f"❌ DB yangilashda xato: {e}")