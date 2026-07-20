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
        "Foydalanuvchi taqdim etgan Nmap, Nikto yoki SQLMap skanerlash loglarini diqqat bilan tahlil qiling. "
        "Sizning asosiy vazifangiz — FAQAT loglarda aniq ko'ringan va tasdiqlangan zaifliklarni tahlil qilishdir.\n\n"
        
        "⚠️ QAT'IY QOIDALAR:\n"
        "1. O'zingizdan xavf yoki ochiq port to'qib chiqarmang (Hallucination taqiqlanadi).\n"
        "2. Agar logda skaner xatolik bergan bo'lsa (masalan: '0 hosts up' yoki 'no usable links found'), "
        "buni zaiflik deb emas, skanerlash muvaffaqiyatsiz bo'lgani yoki parametrlar yetishmasligi deb hisobotda aniq ko'rsating.\n"
        "3. Agar tizimda hech qanday xavf topilmagan bo'lsa, buni ochiqchasiga yozing.\n\n"
        
        "Hisobot formati (O'zbek tilida, qisqa va professional):\n"
        "- **Skanerlash Holati**: Skanerlar to'g'ri ishladi-mi yoki xato berdimi?\n"
        "- **Aniqlangan Haqiqiy Xavflar**: (Faqat logda borlari, bo'lmasa 'Topilmadi' deb yozing)\n"
        "- **Tavsiyalar va Best Practices**: (Real natijaga mos keladigan amaliy yechimlar)"
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