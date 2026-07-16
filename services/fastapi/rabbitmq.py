import os
import aio_pika
import logging
import json

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("fast_api_sendpika")

async def send_result_to_django(slug: str, user_id: int, ai_report: str, status: str = "COMPLETED"):
    
    logger.info(f"📤 Natijani Django'ga yuborish boshlandi (Slug: {slug})")
    try:
        connection = await aio_pika.connect_robust(os.getenv("CELERY_BROKER_URL"))
        
        async with connection:
            channel = await connection.channel()
            
            queue_name = 'web_scan_results'
            queue = await channel.declare_queue(queue_name, durable=True)
            
            result_payload = {
                "slug": slug,
                "user_id": user_id,
                "ai_report": ai_report,
                "status": status
            }
            
            message_body = json.dumps(result_payload).encode('utf-8')
            
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=message_body,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=queue_name
            )
            
            logger.info("✅ Natija RabbitMQ 'web_scan_results' navbatiga muvaffaqiyatli yuborildi!")
            
    except Exception as e:
        logger.error(f"❌ Natijani RabbitMQ-ga yuborishda xatolik: {e}")