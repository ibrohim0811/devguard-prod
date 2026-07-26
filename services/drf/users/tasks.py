import logging
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, ignore_result=True)
def send_otp_email_task(self, email, full_name, otp):
    """
    Asinxron tarzda DevGuard HTML shabloni orqali OTP email yuborish.
    """
    logger.info(f"OTP email yuborilmoqda: {email}")
    
    subject = f"{otp} — DevGuard tasdiqlash kodi"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [email]

    # 1. HTML Shablon uchun context
    context = {
        'full_name': full_name,
        'otp': otp,
    }

    try:
        # 2. HTML mazmunini render qilamiz
        html_content = render_to_string('emails/otp_email.html', context)

        # 3. Plain-text versiya (HTML o'qiy olmaydigan mijozlar va Spam-filtrlar uchun zarur)
        text_content = (
            f"Assalomu alaykum, {full_name}!\n\n"
            f"Sizning DevGuard hisobingizga kirish uchun bir martalik kodingiz: {otp}\n\n"
            f"Ushbu kod 10 daqiqa amal qiladi. Kodni hech kimga bermang."
        )

        # 4. Email xabarini shakllantirish
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=to_email
        )
        msg.attach_alternative(html_content, "text/html")

        # 5. Spamga tushmaslik uchun qo'shimcha Headers (Email yaxshi yetib borishi uchun)
        msg.extra_headers['X-Auto-Response-Suppress'] = 'OOF, AutoReply'
        msg.extra_headers['Auto-Submitted'] = 'auto-generated'

        # Yuborish
        msg.send(fail_silently=False)

        logger.info(f"OTP email muvaffaqiyatli yuborildi: {email}")
        
    except Exception as exc:
        logger.exception(f"Email yuborishda xatolik: {exc}")
        raise self.retry(exc=exc, countdown=5)