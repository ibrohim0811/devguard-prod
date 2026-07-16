# fastapi/scan.py
import asyncio
import shlex
import logging
import re
import os

from .analyze import analyze_logs_with_groq
from .rabbitmq import send_result_to_django

logger = logging.getLogger("fastapi_async_scanner")

DOMEN_REGEX = re.compile(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}$")

async def execute_subprocess_scan_async(url: str, slug: str, user_id: int):
    logger.info(f"🚀 Kengaytirilgan audit boshlanmoqda: {url} (Slug: {slug})")
    
    clean_domain = url.replace("https://", "").replace("http://", "").split('/')[0]

    if not DOMEN_REGEX.match(clean_domain):
        logger.error(f"❌ Noto'g'ri yoki shubhali domen formati rad etildi: {clean_domain}")
        # Agar domen xato bo'lsa ham Djangoga xato statusini qaytaramiz
        await send_result_to_django(slug, user_id, "Xato: Noto'g'ri domen formati!", "FAILED")
        return

    script_path = "./scripts/audit.sh" 
    
    if not os.path.exists(script_path):
        logger.error(f"❌ Skript fayli topilmadi: {script_path}")
        await send_result_to_django(slug, user_id, "Xato: Skanerlash skripti topilmadi!", "FAILED")
        return

    if not os.access(script_path, os.X_OK):
        os.chmod(script_path, 0o755)

    command = f"bash {script_path} {clean_domain}"
    args = shlex.split(command)

    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        logger.info(f"⏳ Skript fonda ishlamoqda (PID: {process.pid})...")
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            logger.info(f"✅ Audit skripti muvaffaqiyatli yakunlandi (Exit Code: 0)")
            
            # 🚀 1. AWAIT bilan AI tahlilini chaqiramiz (Tuzatildi!)
            ai_result = await analyze_logs_with_groq(stdout.decode('utf-8'))
            
            # 🚀 2. Natijani RabbitMQ orqali Django'ga qaytarib yuboramiz!
            await send_result_to_django(slug, user_id, ai_result, "SUCCESS")
            return ai_result
        else:
            error_msg = stderr.decode('utf-8')
            logger.error(f"❌ Skript xatolik bilan tugadi (Exit Code: {process.returncode})")
            logger.error(f"⚠️ Xatolik matni: {error_msg}")
            
            # Skript xato bersa ham Djangoga xabarni yuboramiz
            await send_result_to_django(slug, user_id, f"Auditda xatolik yuz berdi: {error_msg}", "FAILED")

    except Exception as e:
        logger.error(f"💥 Skriptni asinxron ishga tushirishda kutilmagan xato: {e}")
        await send_result_to_django(slug, user_id, f"Tizim xatosi: {str(e)}", "FAILED")