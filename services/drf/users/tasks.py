import os
import logging
import resend
from celery import shared_task
from dotenv import load_dotenv
from jinja2 import FileSystemLoader, Environment

load_dotenv()

logger = logging.getLogger(__name__)

# Resend API kalitini sozlaymiz
resend.api_key = os.getenv("RESEND_API_KEY")

# Jinja2 muhitini bir marta yuklab olamiz
env = Environment(loader=FileSystemLoader("templates/emails"))
template = env.get_template("otp_email.html")


@shared_task(bind=True, max_retries=3, default_retry_delay=5, ignore_result=True)
def send_otp_email_task(self, email: str, full_name: str, otp: str):
    logger.info(f"OTP email yuborilmoqda: {email}")
    
    try:
        # Dinamik parametrlar template'ga beriladi
        rendered_html = template.render(full_name=full_name, otp=otp)
        subject = f"{otp} — DevGuard tasdiqlash kodi"

        response = resend.Emails.send({
            "from": "Devguard <no-reply@devguard.uz>",
            "to": [email],
            "subject": subject,
            "html": rendered_html
        })
        
        logger.info(f"Email muvaffaqiyatli yuborildi: {email}, ID: {response.get('id')}")
        return response

    except Exception as exc:
        logger.error(f"Email yuborishda xatolik ({email}): {exc}")
        # Tarmoq yoki API xatoligi bo'lsa Celery qayta urinib ko'radi (max 3 marta)
        raise self.retry(exc=exc)