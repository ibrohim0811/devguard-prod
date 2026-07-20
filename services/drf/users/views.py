import os
import pika
import json
import random
import uuid
import requests
import logging
import time
from bs4 import BeautifulSoup
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from django.core.cache import cache
from django.utils import timezone  
from dotenv import load_dotenv
from datetime import timedelta

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
StartScanSerializer
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

                        meta_tag = soup.find('meta', attrs={'name': 'devshield'})
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
                                "message":"❌ Sahifada 'devshield' nomli meta teg topilmadi."
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
                        response = requests.get(f"{subdomain}/devshield")
                        print(response)
                        data = response.json()

                        if "devshield" in data:
                            if data["devshield"] == webapp.verification_token:
                                webapp.is_verified = True
                                webapp.save() 
                                return Response({"message":"Vebsaytingiz tasdiqlandi ✅"}, status=status.HTTP_202_ACCEPTED)
                            else:
                                return Response({
                                    "message":"Token mos emas!"
                                }, status=status.HTTP_406_NOT_ACCEPTABLE)
                        else:
                            return Response({
                                    "message":"devshield nomli kalit mavjud emas",
                                    "eslatma": f"{webapp.domain}/devshield endpointiga murojaat qilganda, javob {{'devshield': verification_token}} bo'lishi kerak!"
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

            if last_scan:
                vaqt_farqi = timezone.now() - last_scan.scanned_at

                if vaqt_farqi < timedelta(days=2):
                    return Response({
                        "access": True,
                        "message": "Oxirgi skandan 2 kun o'tmagan. Skanerlash bepul!"
                    }, status=status.HTTP_200_OK)

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


@extend_schema(tags=["web/fullscan"], request=StartScanSerializer)
class FullScanView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        serializer = StartScanSerializer(data=self.request.data)

        if not serializer.is_valid():
            return Response(serializer.error, status=status.HTTP_400_BAD_REQUEST)
        
        slug = serializer.validated_data['slug']
        try:
            web = WebApplications.objects.filter(user=request.user, slug=slug).first()
            transaction = TransactionHistory.objects.filter(webapp=web, user=request.user).order_by("-payment_date").first()
        except WebApplications.DoesNotExist:
            return Response({"error":"BUnday Vebsayt mavjud emas!"}, status=status.HTTP_404_NOT_FOUND)
        
        if not web.is_verified:
            return Response({
                  "message": "Vebsaytingiz hali tekshirilmagan (not verified)!"   
              }, status=status.HTTP_406_NOT_ACCEPTABLE)
        
        last_scan = ScanHistory.objects.filter(webapp=web).order_by('-scanned_at').first()

        if last_scan and last_scan.scanned_at:
            vaqt_farqi = timezone.now() - last_scan.scanned_at
            
            # Agar oxirgi skandan keyin 2 kun (48 soat) o'tmagan bo'lsa
            if vaqt_farqi < timedelta(days=2):
                return Response({
                    "access": True,
                    "message": "Oxirgi skandan 2 kun o'tmagan. Skanerlash hozircha bepul!"
                }, status=status.HTTP_200_OK)
        
        
        
        credentials = pika.PlainCredentials(os.getenv("PIKA_USER"), os.getenv("PIKA_PASSWORD"))

        parameters = pika.ConnectionParameters(
            host='127.0.0.1',
            port=5672,
            virtual_host='/',  # Standart vhost nomi aniq shu!
            credentials=credentials
        )


        try:
            conn = pika.BlockingConnection(parameters=parameters)
            channel = conn.channel()

            queue_name = "fullscan"
            channel.queue_declare(queue=queue_name, durable=True)

            # 1. Vaqtinchalik navbat ochamiz
            reply_queue = channel.queue_declare(queue='', exclusive=True)
            callback_queue = reply_queue.method.queue

            corr_id = str(uuid.uuid4())
            response_data = None

            # 2. Callback funksiya
            def on_response(ch, method, props, body):
                nonlocal response_data
                if props.correlation_id == corr_id:
                    response_data = json.loads(body.decode())
                    ch.basic_ack(delivery_tag=method.delivery_tag)

            channel.basic_consume(queue=callback_queue, on_message_callback=on_response)

            payload = {
                "domain": web.domain,
                "user_id": web.user.id,
                "slug": web.slug
            }

            # 3. Xabarni yuborish
            channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=json.dumps(payload),
                properties=pika.BasicProperties( 
                    delivery_mode=2,
                    reply_to=callback_queue,
                    correlation_id=corr_id
                )
            )

            logger.info(f"⏳ Django '{slug}' uchun FastAPI dan javob kutmoqda...")

            # 🔥 4. CHEKSIZ LOOPdan himoya (Timeout: 60 soniya)
            start_time = time.time()
            timeout_limit = 60  # Maksimal kutish vaqti soniyalarda

            while response_data is None:
                conn.process_data_events(time_limit=1)
                
                # Agar kutish vaqti 60 soniyadan oshib ketgan bo'lsa, sikldan chiqib ketamiz
                if time.time() - start_time > timeout_limit:
                    logger.warning(f"⏰ FastAPI dan javob kutish vaqti tugadi (Timeout): {slug}")
                    break

            conn.close() 

            # 🔥 5. Agar timeout bo'lgan bo'lsa, foydalanuvchiga xato qaytaramiz
            if response_data is None:
                return Response({
                    "error": "Skanerlash jarayoni juda uzoq davom etdi yoki server javob bermadi. Keyinroq qayta urinib ko'ring."
                }, status=status.HTTP_504_GATEWAY_TIMEOUT)

            # 🔥 6. Bazaga xavfsiz saqlash (Agar scan topilmasa, yangi ochadi yoki yangilaydi)
            scan, created = ScanHistory.objects.get_or_create(
                webapp=web,
                defaults={
                    "result_summary": response_data.get("report"),
                }
            )
            
            # Agar obyekt allaqachon bor bo'lsa, shunchaki yangilaymiz
            if not created:
                scan.result_summary = response_data.get("report")
                scan.save()

            return Response({
                "message": "Skanerlash va AI tahlili muvaffaqiyatli yakunlandi 🎉",
                "report": scan.result_summary  # Maydon nomini to'g'riladik
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"RabbitMQ ulanishida yoki jarayonda xato: {e}")
            return Response({
                "error": "Tizim xatoligi (RabbitMQ yoki hisobot kutishda xato) 🔌"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

@extend_schema(tags=["web/scan"], request=StartScanSerializer)
class Scan(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = StartScanSerializer(data=self.request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        slug = serializer.validated_data['slug']
        
        # 1. Obyektlarni xavfsiz tekshirish
        web = WebApplications.objects.filter(user=request.user, slug=slug).first()
        if not web:
            return Response({"error": "Bunday Vebsayt mavjud emas!"}, status=status.HTTP_404_NOT_FOUND)
            
        transaction = TransactionHistory.objects.filter(webapp=web, user=request.user).order_by("-payment_date").first()
        if not transaction or transaction.status != TransactionHistory.StatusChoices.SUCCESS:
            return Response({"error": "To'lov tasdiqlanmagan!"}, status=status.HTTP_402_PAYMENT_REQUIRED)

        if not web.is_verified:
            return Response({"message": "Vebsaytingiz hali tekshirilmagan!"}, status=status.HTTP_466_NOT_ACCEPTABLE)

        # 2. Vaqt cheklovini to'g'ri tekshirish (Bug hal qilindi)
        last_scan = ScanHistory.objects.filter(webapp=web).order_by('-scanned_at').first()

        if last_scan and last_scan.scanned_at:
            vaqt_farqi = timezone.now() - last_scan.scanned_at
            
            # Agar oxirgi skandan keyin 2 kun (48 soat) o'tmagan bo'lsa
            if not vaqt_farqi < timedelta(days=2):
                return Response({
                    "access": True,
                    "message": "Oxirgi skandan 2 kun o'tgan"
                }, status=status.HTTP_402_PAYMENT_REQUIRED)

        # 3. Skanerlash tarixida yangi yozuv ochish yoki yangilash
        scan_record, created = ScanHistory.objects.get_or_create(
            webapp=web,
            defaults={"result_summary": "Skanerlash navbatda..."}
        )
        if not created:
            scan_record.result_summary = "Skanerlash navbatda..."
            scan_record.save()

        # 4. RabbitMQ aloqasi
        credentials = pika.PlainCredentials(os.getenv("PIKA_USER"), os.getenv("PIKA_PASSWORD"))
        parameters = pika.ConnectionParameters(
            host=os.getenv("RABBITMQ_HOST", "127.0.0.1"),
            port=5672,
            virtual_host='/', 
            credentials=credentials
        )

        try:
            conn = pika.BlockingConnection(parameters=parameters)
            channel = conn.channel()
            
            # Asosiy topshiriq navbati
            queue_name = "scan" 
            channel.queue_declare(queue=queue_name, durable=True)

            # 🔥 RPC uchun vaqtinchalik eksklyuziv javob navbatini ochamiz
            result = channel.queue_declare(queue='', exclusive=True)
            callback_queue = result.method.queue

            corr_id = str(uuid.uuid4())
            response_data = None

            # Callback funksiyasi: FastAPI dan aynan shu corr_id bilan kelgan javobni ushlaydi
            def on_response(ch, method, props, body):
                nonlocal response_data
                if props.correlation_id == corr_id:
                    response_data = json.loads(body.decode())
                    ch.basic_ack(delivery_tag=method.delivery_tag)

            # Vaqtinchalik navbatni tinglashni boshlaymiz
            channel.basic_consume(queue=callback_queue, on_message_callback=on_response)

            payload = {
                "task_id": corr_id,
                "domain": web.domain,
                "user_id": web.user.id,
                "slug": web.slug,
                "scan_record_id": scan_record.id
            }

            # Xabarni yuboramiz. reply_to qismiga vaqtinchalik callback_queue ni beramiz
            channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=json.dumps(payload),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    reply_to=callback_queue,  # 🔥 FastAPI javobni mana shu vaqtinchalik navbatga qaytaradi
                    correlation_id=corr_id
                )
            )

            # 🔥 FastAPI dan javob kelguncha HTTP so'rovni ushlab, kutib turamiz
            # (Skanerlash va AI tugaguncha thread shu yerda bloklanadi)
            while response_data is None:
                conn.process_data_events(time_limit=1)

            conn.close()

            # 5. Kelgan natijani bazaga saqlaymiz
            scan_record.result_summary = response_data.get("report", "Tahlil natijasi bo'sh.")
            scan_record.save()

            # Darhol yakuniy natijani foydalanuvchiga qaytaramiz!
            return Response({
                "message": "Skanerlash va AI tahlili muvaffaqiyatli yakunlandi 🎉",
                "report": scan_record.result_summary
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "error": f"Skanerlash jarayonida xato yuz berdi: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)