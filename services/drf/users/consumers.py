import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class ScanProgressConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.task_id = self.scope['url_route']['kwargs']['task_id']
        self.room_group_name = f'scan_{self.task_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def scan_status_update(self, event):
        """FastAPI dan kelgan xabarni front-endga yuboradi va DB ni yangilaydi"""
        message = event['message']

        # Xabarni front-endga yuboramiz
        await self.send(text_data=json.dumps(message))

        scan_status = message.get('status')

        # Scan tugagan bo'lsa (muvaffaqiyatli yoki xatolik) — DB yangilanadi
        if scan_status == 'completed':
            report = message.get('report', '')
            await self._save_report(self.task_id, report, 'completed')

        elif scan_status == 'failed':
            error_msg = message.get('message', 'Skanerlash muvaffaqiyatsiz tugadi.')
            await self._save_report(self.task_id, error_msg, 'failed')

    @database_sync_to_async
    def _save_report(self, task_id: str, report: str, status: str):
        """ScanHistory yozuviga natijani saqlaydi (sinxron DB amal)"""
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