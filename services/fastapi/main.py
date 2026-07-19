import asyncio
import aio_pika
import json
import subprocess
import os


from dotenv import load_dotenv
from analyze import analyze_logs_with_groq

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL")


async def process_scan_task(message: aio_pika.IncomingMessage):
    print("🚨 XABAR KELDI! Qayta ishlash boshlandi...")
    async with message.process():
        try:
            data = json.loads(message.body.decode())
            domain = data.get("domain")
            slug = data.get("slug")
            user_id = data.get("user_id")
            
            print(f"📥 Yangi vazifa keldi: Domain={domain}, Slug={slug}, UserID={user_id}")

            
            script_path = "./scripts/audit.sh" 
            
            print(f"🚀 Subprocess ishga tushmoqda: {script_path} {domain}")
            
            process = await asyncio.create_subprocess_exec(
                script_path, domain,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                scan_result = stdout.decode().strip()
                print(f"✅ Skanerlash muvaffaqiyatli tugadi: {slug}")
                
                r = await analyze_logs_with_groq(scan_result)
                print(f"RESULT: {r}")
                
                try:
                    connection = await aio_pika.connect_robust(RABBITMQ_URL)
                    result_queue_name = "scan_results"
                    
                    result_channel = await connection.channel()
                    await result_channel.declare_queue(result_queue_name, durable=True)
                    
                    response_payload = {
                        "slug": slug,
                        "user_id": user_id,
                        "report": r,
                        "status": "completed"
                    }
                    
                    await result_channel.default_exchange.publish(
                        aio_pika.Message(
                            body=json.dumps(response_payload).encode(),
                            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                        ),
                        routing_key=result_queue_name
                    )
                    print(f"🚀 AI hisoboti '{result_queue_name}' navbatiga muvaffaqiyatli qaytarildi!")
                    
                except Exception as rabbit_err:
                    print(f"❌ Javobni RabbitMQ-ga qaytarishda xato: {rabbit_err}")
            else:
                error_log = stderr.decode().strip()
                print(f"❌ Skanerlashda xatolik yuz berdi ({slug}): {error_log}")
        except Exception as e:
            print(f"⚠️ Xabarni qayta ishlashda kutilmagan xato: {e}")


async def main():
    try:
        print("🚨 MAIN KELDI! Qayta ishlash boshlandi...MAIN")
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()
        
        queue = await channel.declare_queue("fullscan", durable=True)
        
        print("🌐 FastAPI Worker 'web_scan_tasks' navbatini eshitishni boshladi...")
        
        await queue.consume(process_scan_task)

        await asyncio.Future()
    except Exception as e:
        print(f"FASTAPI MAIN XATO:{e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Worker to'xtatildi.")