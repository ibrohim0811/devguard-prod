import asyncio
import aio_pika
import json
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict

from dotenv import load_dotenv
from analyze import analyze_logs_with_groq

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL")

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[task_id] = websocket

    def disconnect(self, task_id: str):
        if task_id in self.active_connections:
            del self.active_connections[task_id]

    async def send_status(self, task_id: str, message: dict):
        if task_id in self.active_connections:
            await self.active_connections[task_id].send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/scan/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await manager.connect(task_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(task_id)


def clean_and_truncate_log(log_text: str, max_chars: int = 5000) -> str:
    """Log faylini Groq limiti uchun qisqartiradi, faqat topilgan natijalarni saqlaydi"""
    lines = log_text.split("\n")
    # Faqat topilgan (FOUND yoki +) qatorlarni ajratib olamiz (dirb natijalari uchun)
    important_lines = [line for line in lines if "+" in line or "FOUND" in line or "DIRECTORY" in line]
    
    # Agar muhim qatorlar bo'lsa ularni, bo'lmasa oxirgi qismini olamiz
    cleaned_text = "\n".join(important_lines) if important_lines else log_text
    
    if len(cleaned_text) > max_chars:
        return cleaned_text[:max_chars] + "\n... [Log juda uzun bo'lgani uchun qisqartirildi] ..."
    return cleaned_text


#------------------------------------
#   1 - CHANNEL: Full Audit Task    
#------------------------------------
async def process_scan_task(message: aio_pika.IncomingMessage):
    print("🚨 [Fullscan] XABAR KELDI! Qayta ishlash boshlandi...")
    async with message.process():
        try:
            reply_to_queue = message.reply_to
            corr_id = message.correlation_id

            data = json.loads(message.body.decode())
            domain = data.get("domain")
            slug = data.get("slug")
            user_id = data.get("user_id")
            task_id = data.get("task_id")
            
            print(f"📥 Yangi vazifa (Fullscan): Domain={domain}, Slug={slug}")
            await manager.send_status(task_id, {
                "status": "processing", 
                "message": "Chuqur audit skanerlash boshlandi..."
            })
            
            script_path = "./scripts/audit.sh" 
            process = await asyncio.create_subprocess_exec(
                script_path, domain,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                scan_result = stdout.decode().strip()
                await manager.send_status(task_id, {
                    "status": "done", 
                    "message": "Audit skanerlash muvaffaqiyatli tugadi ✅"
                })
                
                r = await analyze_logs_with_groq(clean_and_truncate_log(scan_result))
                
                # OPTIMALLASHTIRILGAN: Mavjud kanaldan qayta foydalanamiz
                routing_key = reply_to_queue if reply_to_queue else "fullscan_results"
                connection = await aio_pika.connect_robust(RABBITMQ_URL)
                result_queue_name = "scan_results"

                result_channel = await connection.channel()

                # 1. Navbatni to'g'ri e'lon qilamiz (Bu sening kodingda to'g'ri yozilgan)
                queue = await result_channel.declare_queue(result_queue_name, durable=True)
                response_payload = {
                    "slug": slug,
                    "user_id": user_id,
                    "report": r,
                    "status": "completed"
                }
                
                await result_channel.default_exchange.publish(
                    aio_pika.Message(
                        body=json.dumps(response_payload).encode(),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                        correlation_id=corr_id # Django bilan RPC uzilib qolmasligi uchun buni ham qo'shib ket!
                    ),
                    routing_key=result_queue_name
                )
                
                
                print(f"🚀 AI hisoboti '{routing_key}' navbatiga yuborildi!")
            else:
                error_log = stderr.decode().strip()
                print(f"❌ Skanerlashda xatolik yuz berdi ({slug}): {error_log}")
        except Exception as e:
            print(f"⚠️ Xabarni qayta ishlashda kutilmagan xato: {e}")


#------------------------------------
#   2 - CHANNEL: Regular Scan Task   
#------------------------------------
async def scan(message: aio_pika.IncomingMessage):
    print("🚨 [Scan] XABAR KELDI! Qayta ishlash boshlandi...")
    async with message.process():
        try:
            reply_to_queue = message.reply_to
            corr_id = message.correlation_id

            data = json.loads(message.body.decode())
            domain = data.get("domain")
            slug = data.get("slug")
            user_id = data.get("user_id")
            task_id = data.get("task_id")
            
            print(f"📥 Yangi vazifa (Scan): Domain={domain}, Slug={slug}")
            await manager.send_status(task_id, {
                "status": "processing", 
                "message": "Standart skanerlash boshlandi..."
            })
            
            script_path = "./scripts/scan.sh" 
            process = await asyncio.create_subprocess_exec(
                script_path, domain,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                scan_result = stdout.decode().strip()
                await manager.send_status(task_id, {
                    "status": "done", 
                    "message": "Audit skanerlash muvaffaqiyatli tugadi ✅"
                })
                
                r = await analyze_logs_with_groq(clean_and_truncate_log(scan_result))
                
                # OPTIMALLASHTIRILGAN: Mavjud kanaldan qayta foydalanamiz
                routing_key = reply_to_queue if reply_to_queue else "fullscan_results"
                connection = await aio_pika.connect_robust(RABBITMQ_URL)
                result_queue_name = "scan_results"

                result_channel = await connection.channel()

                # 1. Navbatni to'g'ri e'lon qilamiz (Bu sening kodingda to'g'ri yozilgan)
                queue = await result_channel.declare_queue(result_queue_name, durable=True)
                response_payload = {
                    "slug": slug,
                    "user_id": user_id,
                    "report": r,
                    "status": "completed"
                }
                
                await result_channel.default_exchange.publish(
                    aio_pika.Message(
                        body=json.dumps(response_payload).encode(),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                        correlation_id=corr_id # Django bilan RPC uzilib qolmasligi uchun buni ham qo'shib ket!
                    ),
                    routing_key=result_queue_name
                )
                
                
                print(f"🚀 AI hisoboti '{routing_key}' navbatiga yuborildi!")
            else:
                error_log = stderr.decode().strip()
                print(f"❌ Skanerlashda xatolik yuz berdi ({slug}): {error_log}")
        except Exception as e:
            print(f"⚠️ Xabarni qayta ishlashda kutilmagan xato: {e}")


async def main():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    
    # Prefetch count worker resursini to'g'ri taqsimlaydi
    await channel.set_qos(prefetch_count=2)
    
    queue1 = await channel.declare_queue("scan", durable=True)
    await queue1.consume(scan)
    
    queue2 = await channel.declare_queue("fullscan", durable=True)
    await queue2.consume(process_scan_task)
    
    print("🌐 FastAPI Worker ikkala navbatni ham ('scan' va 'fullscan') eshitmoqda...")
    await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Worker to'xtatildi.")