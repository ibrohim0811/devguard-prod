import uuid
import slugify
from django.db import models
from django.contrib.auth.models import AbstractUser
from rest_framework_simplejwt.tokens import RefreshToken


class Users(AbstractUser):
    full_name = models.CharField(max_length=300)
    phone_number = models.CharField(max_length=13, unique=True, blank=True, null=True)
    avatar = models.ImageField(upload_to="users/avatars/", blank=True, null=True)
    telegram_id = models.BigIntegerField(unique=True, blank=True, null=True)

    def __str__(self):
        return self.email if self.email else self.username
    

    def token(self):

        refresh = RefreshToken.for_user(self)
        access = str(refresh.access_token)

        data = {
            'access':access,
            'refresh':str(refresh)
        }

        return data
    
    def __str__(self):
        return self.username



class WebApplications(models.Model):

    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="webapplication")
    domain = models.URLField(unique=True)
    title = models.CharField(max_length=200)
    is_verified = models.BooleanField(default=False)
    slug = models.SlugField(unique=True)

    verification_token = models.CharField(max_length=500, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Faqat yangi obyekt yaratilayotganda token va slug generatsiya qilamiz
        if not self.pk:
            token = f"devshield-verification:{uuid.uuid4().hex[:18]}"
            self.verification_token = token
            while WebApplications.objects.filter(verification_token=self.verification_token).exists():
                addon = uuid.uuid4().hex[:4]
                self.verification_token = f"{token}-{addon}"
                
            slug = uuid.uuid4().hex[:8]
            self.slug = slug
            while WebApplications.objects.filter(slug=self.slug).exists():
                tail = uuid.uuid4().hex[:4]
                self.slug = f"{slug}-{tail}"
                
        return super().save(*args, **kwargs)

    def verif_token(self):
        data = {
            "verification_token":f"{self.verification_token}"
        }
        return data

    def __str__(self):
        return self.domain


class TransactionHistory(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = 'jarayonda', 'Jarayonda'
        SUCCESS = 'muvaffaqiyatli', 'Muvaffaqiyatli'
        DECLINED = 'bekor qilindi', 'Bekor qilindi'
        TIMEOUT = "muddati o'tdi", "Muddati o'tdi"

    webapp = models.ForeignKey(WebApplications, on_delete=models.CASCADE, related_name="transactions")
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="transactions")
    
    payment_id = models.CharField(max_length=300, unique=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=20000.00) 
    status = models.CharField(max_length=100, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    payment_date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.payment_id:
            self.payment_id = f"devshield_payment_{uuid.uuid4().hex}"
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.amount} UZS ({self.status})"
    

class ScanHistory(models.Model):
    webapp = models.ForeignKey(WebApplications, on_delete=models.CASCADE, related_name="scans")
    scanned_at = models.DateTimeField(auto_now_add=True)
    result_summary = models.JSONField(default=dict) 

    class Meta:
        ordering = ['-scanned_at']