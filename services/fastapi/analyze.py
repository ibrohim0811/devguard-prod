import logging
import httpx
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("fastapi_async_analyzer")


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

async def analyze_logs_with_groq(scan_output: str) -> str:
    
    if not GROQ_API_KEY:
        logger.error("❌ Groq API Key topilmadi!")
        return "Tizim xatoligi: AI tahlili imkonsiz."

    logger.info("🤖 Groq AI orqali loglarni tahlil qilish boshlandi...")

    system_prompt = (
        "Siz tajribali veb xavfsizligi bo'yicha mutaxassissiz. "
        "Foydalanuvchi taqdim etgan tizim va tarmoq loglarini tahlil qiling. "
        "Topilgan ochiq portlar, xizmatlar yoki xavfsizlik kamchiliklarini qisqa, "
        "tushunarli va professional tavsiyalar bilan o'zbek tilida hisobot shaklida yozib bering. "
        "Muhim xavflarni va ularni tuzatish bo'yicha eng yaxshi amaliyotlarni (best practices) keltiring."
    )

    payload = {
        "model": "llama-3.3-70b-versatile",  
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Mana skanerlash natijalari:\n\n{scan_output}"}
        ],
        "temperature": 0.5,
        "max_tokens": 1500
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(GROQ_API_URL, json=payload, headers=headers)
            
            if response.status_code == 200:
                response_data = response.json()
                ai_analysis = response_data['choices'][0]['message']['content']
                logger.info("✅ Groq AI tahlili muvaffaqiyatli yakunlandi!")
                return ai_analysis
            else:
                logger.error(f"❌ Groq API xatosi: {response.status_code} - {response.text}")
                return f"AI tahlilida xatolik yuz berdi. Kod: {response.status_code}"

    except Exception as e:
        logger.error(f"❌ Groq-ga asinxron so'rov yuborishda kutilmagan xato: {e}")
        return "AI tizimi bilan bog'lanishda muammo yuz berdi."