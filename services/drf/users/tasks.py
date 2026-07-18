from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, ignore_result=True)
def send_otp_email_task(self, email, full_name, otp):
    """
    Fonda asinxron tarzda chiroyli HTML formatdagi OTP emailini yuborish.
    Xatolik yuz bersa, 3 marta qayta urinadi.
    """
    logger.info(f"OTP yuborilmoqda: {email}")
    
    subject = "Ro'yxatdan o'tishni tasdiqlang"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [email]

    # HTML shablonini yuklab, ma'lumotlarni joylashtiramiz
    html_content = render_to_string('emails/otp_email.html', {
        'full_name': full_name,
        'otp': otp
    })
    text_content = strip_tags(html_content)

    try:
        msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"OTP muvaffaqiyatli ketdi: {email}")
        return f"Yuborildi: {email}"
        
    except Exception as exc:
        logger.error(f"Email yuborishda xatolik: {exc}. Qayta urinib ko'ramiz...")
        # Tarmoq xatolari yoki SMTP muammosi bo'lsa, 5 soniyadan keyin qayta urinish
        raise self.retry(exc=exc, countdown=5)