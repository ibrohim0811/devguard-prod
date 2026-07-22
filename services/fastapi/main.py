import asyncio
import aio_pika
import json
import os
from fastapi import FastAPI
from redis.asyncio import Redis
from dotenv import load_dotenv

from analyze import analyze_logs_with_groq

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL")

app = FastAPI()

# ------------------------------------
#   Redis Client & Django Signal
# ------------------------------------
# Docker da REDIS_HOST=redis, local da 127.0.0.1
_redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
_redis_port = int(os.getenv("REDIS_PORT", 6379))
redis_client = Redis(host=_redis_host, port=_redis_port, db=0)

async def send_status_to_django(task_id: str, payload: dict):
    """Django Channels'ning Redis guruhiga real-time status yuborish"""
    if not task_id:
        return
    
    channel_layer_name = f'scan_{task_id}'
    
    event = {
        "type": "scan_status_update",  # Django Consumer'dagi funksiya nomi
        "message": payload
    }
    
    # Django channels_redis xabarlarni 'asgi:group:<group_name>' kalitida kutadi
    await redis_client.publish(
        f"asgi:group:{channel_layer_name}",
        json.dumps(event)
    )


def clean_and_truncate_log(log_text: str, max_chars: int = 5000) -> str:
    """Log faylini Groq limiti uchun qisqartiradi, faqat topilgan natijalarni saqlaydi"""
    lines = log_text.split("\n")
    important_lines = [line for line in lines if "+" in line or "FOUND" in line or "DIRECTORY" in line]
    
    cleaned_text = "\n".join(important_lines) if important_lines else log_text
    
    if len(cleaned_text) > max_chars:
        return cleaned_text[:max_chars] + "\n... [Log juda uzun bo'lgani uchun qisqartirildi] ..."
    return cleaned_text


# ------------------------------------
#   1 - CHANNEL: Full Audit Task    
# ------------------------------------
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
            
            # 📢 Django WebSocket orqali front-endga status yuboramiz
            await send_status_to_django(task_id, {
                "status": "processing", 
                "progress": 20,
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
                
                await send_status_to_django(task_id, {
                    "status": "analyzing", 
                    "progress": 70,
                    "message": "Audit tugadi, Groq AI tahlil qilmoqda... 🧠"
                })
                
                r = await analyze_logs_with_groq(clean_and_truncate_log(scan_result))
                
                # Natijani Django kutayotgan navbatga yuboramiz
                routing_key = reply_to_queue if reply_to_queue else "fullscan_results"
                
                response_payload = {
                    "slug": slug,
                    "user_id": user_id,
                    "report": r,
                    "status": "completed"
                }
                
                # Tayyor kanaldan foydalanamiz (Qayta connect qilmaymiz)
                msg = aio_pika.Message(
                    body=json.dumps(response_payload).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    correlation_id=corr_id
                )
                await message.channel.basic_publish(
                    body=msg.body,
                    routing_key=routing_key,
                    properties=msg.properties
                )
                # 📢 Front-endga tugagani haqida xabar beryapmiz
                await send_status_to_django(task_id, {
                    "status": "completed", 
                    "progress": 100,
                    "message": "Audit skanerlash muvaffaqiyatli yakunlandi! 🎉",
                    "report": r
                })
                
                print(f"🚀 AI hisoboti '{routing_key}' navbatiga yuborildi!")
            else:
                error_log = stderr.decode().strip()
                print(f"❌ Skanerlashda xatolik yuz berdi ({slug}): {error_log}")
                await send_status_to_django(task_id, {
                    "status": "failed", 
                    "message": f"Skanerlashda xatolik: {error_log}"
                })
        except Exception as e:
            print(f"⚠️ Xabarni qayta ishlashda kutilmagan xato: {e}")


# ------------------------------------
#   2 - CHANNEL: Regular Scan Task   
# ------------------------------------
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
            
            # 📢 Django WebSocket status
            await send_status_to_django(task_id, {
                "status": "processing", 
                "progress": 20,
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
                print(f"SCAN:{scan_result}")
                await send_status_to_django(task_id, {
                    "status": "analyzing", 
                    "progress": 70,
                    "message": "Skanerlash tugadi, Groq AI tahlil qilmoqda... 🧠"
                })
                
                r = await analyze_logs_with_groq(clean_and_truncate_log(scan_result))
                
                routing_key = reply_to_queue if reply_to_queue else "scan_results"
                
                response_payload = {
                    "slug": slug,
                    "user_id": user_id,
                    "report": r,
                    "status": "completed"
                }
                
                

                # 2. Xabarni yuboramiz
                msg = aio_pika.Message(
                    body=json.dumps(response_payload).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    correlation_id=corr_id
                )
                await message.channel.basic_publish(
                    body=msg.body,
                    routing_key=routing_key,
                    properties=msg.properties
                )
                
                # 📢 Front-endga tugagani haqida xabar
                await send_status_to_django(task_id, {
                    "status": "completed", 
                    "progress": 100,
                    "message": "Standart skanerlash muvaffaqiyatli yakunlandi! 🎉",
                    "report": r
                })
                
                print(f"🚀 AI hisoboti '{routing_key}' navbatiga yuborildi!")
            else:
                error_log = stderr.decode().strip()
                print(f"❌ Skanerlashda xatolik yuz berdi ({slug}): {error_log}")
                await send_status_to_django(task_id, {
                    "status": "failed", 
                    "message": f"Skanerlashda xatolik: {error_log}"
                })
        except Exception as e:
            print(f"⚠️ Xabarni qayta ishlashda kutilmagan xato: {e}")


# ------------------------------------
#   Main Runner
# ------------------------------------
async def main():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    
    # Prefetch count: Har bir worker birdaniga 2 tadan ko'p vazifa olmasligi uchun
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