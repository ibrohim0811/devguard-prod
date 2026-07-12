# 🛡️ DevShield

<p align="center">
  <img src="https://img.shields.io/badge/Django_REST_Framework-092E20?style=for-the-badge&logo=django&logoColor=white" alt="DRF">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/RabbitMQ-FF6600?style=for-the-badge&logo=rabbitmq&logoColor=white" alt="RabbitMQ">
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
</p>

**DevShield** — bu Django REST Framework (DRF), FastAPI va RabbitMQ (Pika) ekotizimiga asoslangan, yuqori yuklamalarga chidamliligi bilan ajralib turadigan mikroservis arxitekturali asenkron hujjat (PDF) yaratish va monetizatsiya platformasi.

Ushbu loyiha uzoq vaqt talab qiladigan og'ir jarayonlarni (masalan, murakkab PDF generatsiya qilish) asosiy veb-serverni (DRF) bloklamagan holda fonda bajarish va pullik funksiyalarni asenkron to'lov mexanizmlari (Telegram Stars / Webhooks) orqali boshqarish imkonini beradi.

---

## 🏗️ Tizim Arxitekturasi va Ishlash Prinsipi

Loyiha **Event-Driven (Hodisalarga asoslangan)** arxitektura ustiga qurilgan:

1. **User ➡️ DRF:** Foydalanuvchi ma'lumotlarni yuboradi. DRF ma'lumotni qabul qilib, Postgres bazasiga `awaiting_payment` yoki `pending` statusi bilan yozadi.
2. **DRF ➡️ RabbitMQ (Pika):** DRF vazifani navbatga qo'yadi va foydalanuvchiga darhol `202 Accepted` javobini qaytaradi (Foydalanuvchi kutib qolmaydi).
3. **RabbitMQ ➡️ FastAPI (Worker):** FastAPI fondagi navbatdan (`pdf_tasks`) xabarni oladi va PDF yaratish (Heavy Processing) amalini boshlaydi.
4. **FastAPI ➡️ DRF:** PDF tayyor bo'lgach, FastAPI natijani (S3 URL yoki fayl linkini) `pdf_results` navbatiga qaytaradi.
5. **DRF ➡️ User:** Alohida fonda ishlovchi Consumer natijani olib, bazani yangilaydi hamda foydalanuvchiga **Email** va **Push Notification** orqali xabar yuboradi.

---

## 🚀 Texnologik Stak

* **Backend (API Gateway & Auth):** Django REST Framework (DRF) + JWT Authentication
* **Background Worker (PDF Generator):** FastAPI (Asenkron rejim)
* **Message Broker:** RabbitMQ (Pika / `aio-pika`)
* **Database:** PostgreSQL (Asosiy ma'lumotlar va tasklar tarixi uchun)
* **Caching & Real-time:** Redis
* **Konteynerizatsiya:** Docker + Docker Compose (Versiyalar buzilib ketmasligi va xavfsiz muhit uchun)

---

## 🛠️ O'rnatish va Ishga Tushirish
# Tez orada bu loyiha https://devshield.uz domainida ishlashni boshlaydi!

### 1. Loyihani klonlash
```bash
git clone [https://github.com/yourusername/devshield.git](https://github.com/yourusername/devshield.git)
cd devshield