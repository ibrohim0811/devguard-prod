import os
import pika
import json
import random
import uuid
import requests
import logging
from bs4 import BeautifulSoup
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from django.core.cache import cache
from django.utils import timezone  
from dotenv import load_dotenv
from datetime import timedelta
from django.shortcuts import get_object_or_404

load_dotenv()

logger = logging.getLogger(__name__)



from rest_framework.generics import (
    DestroyAPIView,
    RetrieveAPIView, RetrieveUpdateAPIView,
    ListCreateAPIView, ListAPIView
)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView

from .serializers import( 
RegisterSerializer, ProfileSerializer, 
WebApplicationsSerializer, TransactionSerializer,
VerifyOTPSerializer, ResendOTPSerializer, CheckPaymentSerializer,
StartScanSerializer, ScanHistorySerializer
)

from django.conf import settings
from django.contrib.auth.hashers import make_password

from .models import Users, WebApplications, TransactionHistory, ScanHistory
from .tasks import send_otp_email_task


@extend_schema(tags=['Register'])
class RegisterCreateAPIView(APIView):
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            validated_data = serializer.validated_data
            email = validated_data['email']
            full_name = validated_data.get('full_name', 'Foydalanuvchi')
            
            otp = str(random.randint(100000, 999999))

            user_temp_data = {
                "full_name": full_name,
                "phone_number": validated_data['phone_number'],
                "email": email,
                "password": make_password(validated_data['password'])
            }

            cache.set(f"temp_user:{email}", user_temp_data, timeout=600)
            cache.set(f"otp:{email}", otp, timeout=600)

            
            send_otp_email_task.delay(email, full_name, otp)

            return Response({
                "message": "Tasdiqlash kodi emailingizga yuborildi."
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Register'])
class VerifyOTPAPIView(APIView):
    serializer_class = VerifyOTPSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp_entered = serializer.validated_data['otp']

            saved_otp = cache.get(f"otp:{email}")
            user_data = cache.get(f"temp_user:{email}")

            if not saved_otp or not user_data:
                return Response(
                    {"error": "Kod muddati tugagan yoki noto'g'ri so'rov!"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            if saved_otp == otp_entered:
                
                if Users.objects.filter(email=email).exists():
                    return Response(
                        {"error": "Ushbu email allaqachon ro'yxatdan o'tgan!"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if Users.objects.filter(phone_number=user_data['phone_number']).exists():
                    return Response(
                        {"error": "Ushbu telefon raqam allaqachon ro'yxatdan o'tgan!"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

                try:
                    user = Users.objects.create(
                        username=user_data['phone_number'],  
                        phone_number=user_data['phone_number'],
                        email=user_data['email'],
                        full_name=user_data['full_name'],
                        password=user_data['password']  
                    )
                    user.save()

                    response_data = {
                        "id": user.id,
                        "full_name": user.full_name,
                        "phone_number": user.phone_number,
                        "email": user.email,
                    }
                    
                    response_data.update(user.token())

                    cache.delete(f"temp_user:{email}")
                    cache.delete(f"otp:{email}")

                    return Response(response_data, status=status.HTTP_201_CREATED)

                except Exception as e:
                    return Response(
                        {"error": f"Foydalanuvchini saqlashda xatolik: {str(e)}"}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            else:
                return Response(
                    {"error": "Kiritilgan tasdiqlash kodi noto'g'ri!"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Register'])
class ResendOTPAPIView(APIView):
    serializer_class = ResendOTPSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']

            user_data = cache.get(f"temp_user:{email}")
            if not user_data:
                return Response(
                    {"error": "Ushbu email uchun faol ro'yxatdan o'tish jarayoni topilmadi. Avval ro'yxatdan o'ting!"}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            cooldown_active = cache.get(f"resend_cooldown:{email}")
            if cooldown_active:
                return Response(
                    {"error": "Yangi kod so'rash uchun 60 soniya kuting!"}, 
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )

            new_otp = str(random.randint(100000, 999999))
            cache.set(f"otp:{email}", new_otp, timeout=600)  
            cache.set(f"resend_cooldown:{email}", "blocked", timeout=60)

            full_name = user_data.get('full_name', 'Foydalanuvchi')

            try:
            
                send_otp_email_task.delay(email, full_name, new_otp)

                return Response({
                    "message": "Yangi tasdiqlash kodi emailingizga qayta yuborildi."
                }, status=status.HTTP_200_OK)

            except Exception as e:
                return Response({
                    "error": f"Tizim xatoligi (Broker ulanishi): {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@extend_schema(tags=['user/Profile'])
class ProfileRetrieveAPIView(RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated, ]

    def get_object(self):
        return self.request.user
    


@extend_schema(tags=['user/webapps'])
class WebApplicationsListCreateView(ListCreateAPIView):
    serializer_class = WebApplicationsSerializer
    permission_classes = [IsAuthenticated, ]

    def get_queryset(self):
        return WebApplications.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)



@extend_schema(tags=['user/webapps'])
class WebApplicationsDetailView(RetrieveAPIView):
    serializer_class = WebApplicationsSerializer
    permission_classes = [IsAuthenticated, ]
    lookup_field = "slug"

    def get_queryset(self):
        return WebApplications.objects.filter(user=self.request.user)
    

@extend_schema(tags=["user/webapps"])
class WebApplicationDeleteBySlugAPIView(DestroyAPIView):
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug' 

    def get_queryset(self):
        return WebApplications.objects.filter(user=self.request.user)
        

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"message": f"Sayt ({instance.domain}) muvaffaqiyatli o'chirildi! ✅"}, 
            status=status.HTTP_204_NO_CONTENT
        )
    


@extend_schema(tags=["user/payment"])
class TransactionListCreateAPIView(ListAPIView):
    queryset = TransactionHistory.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated, ]

    

@extend_schema(tags=["user/payment"])
class TransactionDetailAPIView(RetrieveAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated, ]
    lookup_field = "payment_id" 
    lookup_url_kwarg = "payment_id"

    def get_queryset(self):
        return TransactionHistory.objects.filter(user=self.request.user)
    


@extend_schema(tags=['services/check'])
@api_view(['GET'])
@permission_classes([IsAuthenticated, ])
def checkwebtoken(request, slug):

    if request.method == 'GET':
        print(f"slug:{slug}")
        webapp = WebApplications.objects.filter(user=request.user, slug=slug).first()
        
        if webapp:
            if not webapp.is_verified:
                if not webapp.is_subdomain:
                    web = webapp
                    web_link = web.domain
                    token = web.verification_token
                    
                    try:
                        response = requests.get(web_link, timeout=10)
                        soup = BeautifulSoup(response.text, 'html.parser')

                        meta_tag = soup.find('meta', attrs={'name': 'devguard'})
                        if meta_tag:
                            
                            web_token = meta_tag.get('content')
                            
                            if web_token == token:
                                web.is_verified = True
                                web.save()
                                return Response({
                                    "success":True,
                                    "message":"Saytingiz tasdiqlandi ✅",
                                    
                                }, status=status.HTTP_200_OK)
                            else:
                                return Response({
                                    "success":True,
                                    "message":"Saytingizdagi token mos emas ⛔"
                                }, status=status.HTTP_400_BAD_REQUEST)
                        else:
                            return Response({
                                "success":True,
                                "message":"❌ Sahifada 'devguard' nomli meta teg topilmadi."
                            }, status=status.HTTP_400_BAD_REQUEST)
                    except requests.exceptions.RequestException as e:
                        print(f"checkweb:{e}")
                        return Response({
                                "success":False,
                                "message":"Serverda Xatolik!"
                            }, status=status.HTTP_502_BAD_GATEWAY)  
                else:
                    if not webapp.is_verified:
                        subdomain = webapp.domain
                        if not subdomain.startswith(('http://', 'https://')):
                            subdomain = f"https://{subdomain}"
                        response = requests.get(f"{subdomain}/devguard")
                        print(response)
                        data = response.json()

                        if "devguard" in data:
                            if data["devguard"] == webapp.verification_token:
                                webapp.is_verified = True
                                webapp.save() 
                                return Response({"message":"Vebsaytingiz tasdiqlandi ✅"}, status=status.HTTP_202_ACCEPTED)
                            else:
                                return Response({
                                    "message":"Token mos emas!"
                                }, status=status.HTTP_406_NOT_ACCEPTABLE)
                        else:
                            return Response({
                                    "message":"devguard nomli kalit mavjud emas",
                                    "eslatma": f"{webapp.domain}/devguard endpointiga murojaat qilganda, javob {{'devguard': verification_token}} bo'lishi kerak!"
                                }, status=status.HTTP_406_NOT_ACCEPTABLE)
                    else:
                        return Response({"message":"Bu Vebsayt tekshirilgan"}, status=status.HTTP_200_OK)
            else:
                return Response({
                    "success":True,
                    "message":"Vebsaytingiz avval tekshirilgan"
                }, status=status.HTTP_406_NOT_ACCEPTABLE)    
    return Response({
        "success":True,
        "message":"Permission Denied!"
    }, status=status.HTTP_405_METHOD_NOT_ALLOWED)       
                    

@extend_schema(tags=["webapp/payment"], request=CheckPaymentSerializer)
@permission_classes([IsAuthenticated, ])
class CheckWebappPayment(APIView):

    
    def post(self, request):
        
        serializer = CheckPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        slug = slug = serializer.validated_data['webapp_slug']
        user = request.user
        
        try:
            webapp = WebApplications.objects.get(slug=slug, user=user)
        except WebApplications.DoesNotExist:
            return Response({"error": "Sayt topilmadi!"}, status=status.HTTP_404_NOT_FOUND)
        
        if webapp.is_verified:

            last_scan = ScanHistory.objects.filter(webapp=webapp).order_by('-scanned_at').first()

            if last_scan and last_scan.scanned_at:
                vaqt_farqi = timezone.now() - last_scan.scanned_at
                if vaqt_farqi > timedelta(days=2):
                    return Response({
                        "access": False,
                        "message": "Oxirgi skanerdan 2 kun o'tdi. Qayta skanerlash uchun to'lov qiling."
                }, status=status.HTTP_402_PAYMENT_REQUIRED)

            transaction = TransactionHistory.objects.create(
                webapp=webapp,
                user=user,
                amount=20000.00,
                status=TransactionHistory.StatusChoices.PENDING
            )

            
            deeplink = f"https://t.me/{os.getenv("BOT_USERNAME")}?start={transaction.payment_id}"

            return Response({
                "access": False,
                "message": "Skanerlash muddati tugagan. Iltimos to'lov qiling.",
                "deeplink": deeplink
            }, status=status.HTTP_402_PAYMENT_REQUIRED)
        return Response({
            "access":False,
            "message":"Vebsaytingiz tasdiqdan o'tmagan"
        }, status=status.HTTP_406_NOT_ACCEPTABLE)


def get_rabbitmq_connection():
    """RabbitMQ ulanish parametrlari uchun yordamchi funksiya"""
    credentials = pika.PlainCredentials(
        os.getenv("PIKA_USER", "guest"), 
        os.getenv("PIKA_PASSWORD", "guest")
    )
    parameters = pika.ConnectionParameters(
        host=os.getenv("RABBITMQ_HOST", "127.0.0.1"),
        port=5672,
        virtual_host='/',
        credentials=credentials
    )
    return pika.BlockingConnection(parameters)


@extend_schema(tags=["web/scan"], request=StartScanSerializer)
class FullScanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = StartScanSerializer(data=self.request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        slug = serializer.validated_data['slug']
        
        web = WebApplications.objects.filter(user=request.user, slug=slug).first()
        if not web:
            return Response({"error": "Bunday Vebsayt mavjud emas!"}, status=status.HTTP_404_NOT_FOUND)
            
        has_successful_payment = TransactionHistory.objects.filter(
            webapp=web, 
            user=request.user, 
            status=TransactionHistory.StatusChoices.SUCCESS
        ).exists()
        if not has_successful_payment:
            return Response({"error": "To'lov tasdiqlanmagan!"}, status=status.HTTP_402_PAYMENT_REQUIRED)
        if not web.is_verified:
            return Response({"message": "Vebsaytingiz hali tekshirilmagan!"}, status=status.HTTP_466_NOT_ACCEPTABLE)

        # Vaqt cheklovini tekshirish
        last_scan = ScanHistory.objects.filter(webapp=web).order_by('-scanned_at').first()
        if last_scan and last_scan.scanned_at:
            vaqt_farqi = timezone.now() - last_scan.scanned_at
            if vaqt_farqi > timedelta(days=2):
                return Response({
                    "access": False,
                    "message": "Oxirgi skanerdan 2 kun o'tdi. Qayta skanerlash uchun to'lov qiling."
                }, status=status.HTTP_402_PAYMENT_REQUIRED)

        # Base yozuv ochish
        scan_record, created = ScanHistory.objects.get_or_create(
            webapp=web,
            defaults={"result_summary": "Chuqur skanerlash navbatda..."}
        )
        if not created:
            scan_record.result_summary = "Chuqur skanerlash navbatda..."
            scan_record.save()

        try:
            conn = get_rabbitmq_connection()
            channel = conn.channel()

            queue_name = "fullscan"
            channel.queue_declare(queue=queue_name, durable=True)

            # 🔥 FIRE AND FORGET: task_id = corr_id sifatida ishlatiladi
            # WebSocket consumer shu task_id orqali qaysi scan yozuvini
            # yangilashni biladi (scan_record ga ham saqlaymiz)
            corr_id = str(uuid.uuid4())

            # task_id ni scan_record ga bog'laymiz
            scan_record.task_id = corr_id
            scan_record.save(update_fields=['task_id'])

            payload = {
                "task_id": corr_id, 
                "domain": web.domain,
                "user_id": web.user.id,
                "slug": web.slug,
                "scan_record_id": scan_record.id
            }

            channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=json.dumps(payload),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    correlation_id=corr_id
                )
            )
            conn.close()

            logger.info(f"✅ Fullscan navbatga qo'shildi: task_id={corr_id}, slug={slug}")

            # ✅ Darhol javob qaytaramiz — HTTP so'rov bloklanmaydi!
            # Front-end WebSocket ws://host/ws/scan/{task_id}/ ga ulanib
            # real-time xabarlarni qabul qiladi.
            host = request.get_host()  # 'api.devguard.uz' yoki 'localhost:8000'
            return Response({
                "message": "Chuqur skanerlash navbatga qo'shildi. WebSocket orqali natijani kuting.",
                "task_id": corr_id,
                "websocket_url": f"wss://{host}/ws/scan/{corr_id}/"
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            logger.error(f"FullScan RabbitMQ xatoligi: {e}")
            return Response({
                "error": f"Skanerlash jarayonida xato yuz berdi: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(tags=["web/scan"], request=StartScanSerializer)
class Scan(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = StartScanSerializer(data=self.request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        slug = serializer.validated_data['slug']
        
        web = WebApplications.objects.filter(user=request.user, slug=slug).first()
        if not web:
            return Response({"error": "Bunday Vebsayt mavjud emas!"}, status=status.HTTP_404_NOT_FOUND)
            
        has_successful_payment = TransactionHistory.objects.filter(
            webapp=web, 
            user=request.user, 
            status=TransactionHistory.StatusChoices.SUCCESS
        ).exists()
        if not has_successful_payment:
            return Response({"error": "To'lov tasdiqlanmagan!"}, status=status.HTTP_402_PAYMENT_REQUIRED)
             
        if not web.is_verified:
            return Response({"message": "Vebsaytingiz hali tekshirilmagan!"}, status=status.HTTP_466_NOT_ACCEPTABLE)

        # 2. Vaqt cheklovini to'g'ri tekshirish
        last_scan = ScanHistory.objects.filter(webapp=web).order_by('-scanned_at').first()
        # ✅ TO'G'RI VARIANT:
        if last_scan and last_scan.scanned_at:
            vaqt_farqi = timezone.now() - last_scan.scanned_at
            if vaqt_farqi > timedelta(days=2):
                return Response({
                    "access": False,
                    "message": "Oxirgi skanerdan 2 kun o'tdi. Qayta skanerlash uchun to'lov qiling."
        }, status=status.HTTP_402_PAYMENT_REQUIRED)

        scan_record, created = ScanHistory.objects.get_or_create(
            webapp=web,
            defaults={"result_summary": "Skanerlash navbatda..."}
        )
        if not created:
            scan_record.result_summary = "Skanerlash navbatda..."
            scan_record.save()

        try:
            conn = get_rabbitmq_connection()
            channel = conn.channel()

            queue_name = "scan"
            channel.queue_declare(queue=queue_name, durable=True)

            # 🔥 FIRE AND FORGET: task_id = corr_id sifatida ishlatiladi
            # WebSocket consumer shu task_id orqali qaysi scan yozuvini
            # yangilashni biladi (scan_record ga ham saqlaymiz)
            corr_id = str(uuid.uuid4())

            # task_id ni scan_record ga bog'laymiz
            scan_record.task_id = corr_id
            scan_record.save(update_fields=['task_id'])

            payload = {
                "task_id": corr_id,
                "domain": web.domain,
                "user_id": web.user.id,
                "slug": web.slug,
                "scan_record_id": scan_record.id
            }

            channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=json.dumps(payload),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    correlation_id=corr_id
                )
            )
            conn.close()

            logger.info(f"✅ Scan navbatga qo'shildi: task_id={corr_id}, slug={slug}")

            # ✅ Darhol javob qaytaramiz — HTTP so'rov bloklanmaydi!
            # Front-end WebSocket ws://host/ws/scan/{task_id}/ ga ulanib
            # real-time xabarlarni qabul qiladi.
            host = request.get_host()  # 'api.devguard.uz' yoki 'localhost:8000'
            return Response({
                "message": "Skanerlash navbatga qo'shildi. WebSocket orqali natijani kuting.",
                "task_id": corr_id,
                "websocket_url": f"wss://{host}/ws/scan/{corr_id}/"
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            logger.error(f"Scan RabbitMQ xatoligi: {e}")
            return Response({
                "error": f"Skanerlash jarayonida xato yuz berdi: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@extend_schema(tags=["web/scan-history"])
class ScanHistoryLIstView(ListAPIView):
    permission_classes = [IsAuthenticated] 
    serializer_class = ScanHistorySerializer
    lookup_field = "slug"

    def get_queryset(self):
        slug = self.kwargs.get(self.lookup_field)

        web = get_object_or_404(WebApplications, slug=slug, user=self.request.user)
        return ScanHistory.objects.filter(webapp=web).order_by('-scanned_at')
    
        