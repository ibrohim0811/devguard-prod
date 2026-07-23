from django.core.mail import send_mail
from django.conf import settings
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, ignore_result=True)
def send_otp_email_task(self, email, full_name, otp):
    """
    Fonda asinxron tarzda oddiy matnli OTP emailini yuborish.
    """
    logger.info(f"OTP yuborilmoqda: {email}")
    
    subject = "Ro'yxatdan o'tishni tasdiqlang"
    message = f"Assalomu alaykum, {full_name}!\n\nSizning tasdiqlash kodingiz: {otp}\n\nKodni hech kimga bermang."
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [email]

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=to_email,
            fail_silently=False  # Xatolik bo'lsa darhol exception ko'taradi
        )
        logger.info(f"OTP muvaffaqiyatli ketdi: {email}")
        
    except Exception as exc:
        logger.exception(f"Email yuborishda xatolik yuz berdi: {exc}")
        raise self.retry(exc=exc, countdown=5)