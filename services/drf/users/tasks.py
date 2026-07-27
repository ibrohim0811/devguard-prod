import os
import logging
import resend
from celery import shared_task
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5, ignore_result=True)
def send_otp_email_task(self, email: str, full_name: str, otp: str):
    logger.info(f"OTP email yuborilmoqda: {email}")

    # 1. Resend API kalitini o'rnatish
    api_key = getattr(settings, 'RESEND_API_KEY', os.getenv("RESEND_API_KEY"))
    if not api_key:
        logger.error("RESEND_API_KEY topilmadi!")
        return
    
    resend.api_key = api_key

    try:
        # 2. Django render_to_string orqali HTML render qilish
        context = {
            "full_name": full_name,
            "otp": otp,
        }
        rendered_html = render_to_string("emails/otp_email.html", context)

        subject = f"{otp} — DevGuard tasdiqlash kodi"

        # 3. Resend API orqali email yuborish
        response = resend.Emails.send({
            "from": getattr(settings, 'DEFAULT_FROM_EMAIL', "DevGuard <no-reply@devguard.uz>"),
            "to": [email],
            "subject": subject,
            "html": rendered_html
        })

        logger.info(f"Email muvaffaqiyatli yuborildi: {email}, ID: {response.get('id')}")
        return response

    except Exception as exc:
        logger.error(f"Email yuborishda xatolik ({email}): {exc}")
        # Celery orqali qayta urinish (Retry)
        raise self.retry(exc=exc)