import asyncio
import aio_pika
import json
import os
import asyncpg
from channels_redis.core import RedisChannelLayer
from fastapi import FastAPI
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
channel_layer = RedisChannelLayer(
    hosts=[f"redis://{_redis_host}:{_redis_port}/0"],
)

async def send_status_to_django(task_id: str, payload: dict):
    """Django Channels'ning Redis guruhiga real-time status yuborish"""
    if not task_id:
        return
    
    # ``group_send`` is required: publishing to ``asgi:group:*`` does not
    # implement the Channels Redis group protocol and drops the event.
    await channel_layer.group_send(
        f"scan_{task_id}",
        {
            "type": "scan_status_update",
            "message": payload,
        },
    )


# ------------------------------------
#   PostgreSQL Direct Updater (Fallback)
# ------------------------------------
DB_NAME = os.getenv("NAME", "devshield")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
if not DB_PASSWORD:
    raise RuntimeError("DB_PASSWORD environment variable is required and missing!")
DB_HOST = os.getenv("HOST", "postgres")
DB_PORT = os.getenv("PORT", "5432")

async def update_scan_history_in_db(task_id: str, report: str):
    """Saves AI summary directly to PostgreSQL database"""
    if not task_id:
        return
    hosts_to_try = [DB_HOST, "127.0.0.1", "localhost"]
    # Unikal hostlar ro'yxatini tartib bilan saqlaymiz
    hosts = list(dict.fromkeys(hosts_to_try))
    
    for host in hosts:
        try:
            conn = await asyncpg.connect(
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                host=host,
                port=int(DB_PORT)
            )
            try:
                query = "UPDATE users_scanhistory SET result_summary = $1 WHERE task_id = $2::uuid"
                status = await conn.execute(query, report, task_id)
                print(f"✅ DB UPDATE via asyncpg ({host}): task_id={task_id}, status={status}")
                return
            finally:
                await conn.close()
        except Exception as e:
            print(f"⚠️ DB UPDATE attempt failed for host {host}: {e}")


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
                
                # Natijani bazaga saqlaymiz
                await update_scan_history_in_db(task_id, r)
                
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
                await update_scan_history_in_db(task_id, f"Skanerlashda xatolik: {error_log}")
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
                
                # Natijani bazaga saqlaymiz
                await update_scan_history_in_db(task_id, r)
                
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
                await update_scan_history_in_db(task_id, f"Skanerlashda xatolik: {error_log}")
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
