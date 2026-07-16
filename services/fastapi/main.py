# fastapi/main.py
import asyncio
import logging
import json
import os
import aio_pika
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv

# Biz tuzatgan scan funksiyasini import qilamiz
from scan import execute_subprocess_scan_async

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("fastapi_main")


async def on_message_received(message: aio_pika.IncomingMessage):
    """
    Django yuborgan 'web_scan_tasks' navbatidan yangi xabar kelganda ishlovchi funksiya.
    """
    async with message.process(): # Avtomatik ravishda basic_ack (tasdiqlash) qiladi
        logger.info("📥 Django'dan yangi vazifa qabul qilindi!")
        try:
            # Kelgan payloadni o'qiymiz
            data = json.loads(message.body.decode('utf-8'))
            url = data.get("url")
            slug = data.get("slug")
            user_id = data.get("user_id") or data.get("user")  # JSON kalitlariga moslash

            if not url:
                logger.warning("⚠️ Xabarda URL topilmadi, xabar bekor qilindi.")
                return

            # 🚀 Skanerlashni asinxron boshlaymiz (Biz yuqorida tuzatgan funksiya)
            await execute_subprocess_scan_async(url, slug, user_id)

        except Exception as e:
            logger.error(f"⚠️ Xabarni qayta ishlashda xatolik: {e}")


async def start_rabbitmq_consumer():
    """
    RabbitMQ-ga asinxron ulanib, vazifalarni doimiy eshitib turuvchi funksiya.
    """
    try:
        broker_url = os.getenv("CELERY_BROKER_URL") or "amqp://guest:guest@localhost:5672/"
        connection = await aio_pika.connect_robust(broker_url)
        channel = await connection.channel()

        # Bir vaqtda faqat 1 ta og'ir taskni olish (Fair Dispatch)
        await channel.set_qos(prefetch_count=1)

        # Django yuboradigan navbatni e'lon qilamiz
        queue = await channel.declare_queue('web_scan_tasks', durable=True)

        logger.info("[*] 🟢 RabbitMQ Asinxron Worker eshitishni boshlamoqda...")
        await queue.consume(on_message_received)

        # Task yopilib ketmasligi uchun asinxron kutish rejimiga o'tamiz
        await asyncio.Future()

    except Exception as e:
        logger.error(f"💥 RabbitMQ Consumer ulanishida xato: {e}")


# 🚀 FastAPI Lifespan (Ishga tushish va to'xtash jarayonini boshqarish)
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("⚡ FastAPI server ishga tushmoqda...")
    
    # RabbitMQ Consumer'ni orqa fonda parallel asinxron vazifa sifatida boshlaymiz
    consumer_task = asyncio.create_task(start_rabbitmq_consumer())
    logger.info("🟢 Orqa fondagi RabbitMQ Consumer task yaratildi.")
    
    yield  # FastAPI shu yerda normal so'rovlarni qabul qilib ishlayveradi
    
    logger.info("🔌 FastAPI server to'xtatilmoqda...")
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        logger.info("✅ Orqa fondagi Consumer task toza yopildi.")


# FastAPI loyihasini lifespan bilan yaratamiz
app = FastAPI(
    title="DevShield Security Audit Service",
    version="1.1.0",
    lifespan=lifespan
)

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "FastAPI ishlamoqda, RabbitMQ Worker orqa fonda faol!"}