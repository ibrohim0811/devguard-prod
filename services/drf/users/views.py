import os
import pika
import json
import random
import requests
import logging
from bs4 import BeautifulSoup
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from django.core.cache import cache
from datetime import timezone, timedelta
from dotenv import load_dotenv

load_dotenv()


from rest_framework.generics import (
    DestroyAPIView,
    RetrieveAPIView, RetrieveUpdateAPIView,
    ListCreateAPIView
)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView

from .serializers import( 
RegisterSerializer, ProfileSerializer, 
WebApplicationsSerializer, TransactionSerializer,
VerifyOTPSerializer, ResendOTPSerializer, CheckPaymentSerializer,
StartScanSerializer
)
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
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
class TransactionListCreateAPIView(ListCreateAPIView):
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
                Response({
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




# logger = logging.getLogger(__name__)
# @extend_schema(tags=["web/full-scan"])
# class StartScanView(APIView):
#     permission_classes = [IsAuthenticated]
#     serializer_class = StartScanSerializer
#     def post(self, request, *args, **kwargs):
#         serializer = self.serializer_class(data=request.data)

#         if not serializer.is_valid():
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#         slug = serializer.validated_data['slug']

#         try:
#             web = WebApplications.objects.get(user=request.user, slug=slug)
#         except WebApplications.DoesNotExist:
#             return Response(
#                 {"error": "Sizga tegishli bo'lgan bunday vebsayt topilmadi!"}, 
#                 status=status.HTTP_404_NOT_FOUND
#             )

#         if not web.is_verified:
#             return Response({
#                 "message": "Vebsaytingiz hali tekshirilmagan (not verified)!"   
#             }, status=status.HTTP_406_NOT_ACCEPTABLE)

#         try:
#             connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
#             channel = connection.channel()

#             queue_name = 'web_scan_tasks'
#             channel.queue_declare(queue=queue_name, durable=True)

#             payload = {
#                 "url": web.domain,      
#                 "user_id": web.user.id,  
#                 "slug": web.slug
#             }

#             message_body = json.dumps(payload)

#             channel.basic_publish(
#                 exchange='',
#                 routing_key=queue_name,
#                 body=message_body,
#                 properties=pika.BasicProperties( 
#                     delivery_mode=2,             
#                 )
#             )

#             connection.close() 

#             return Response({
#                 "message": "Skanerlash muvaffaqiyatli navbatga qo'shildi! 🚀",
#                 "status": "QUEUED"
#             }, status=status.HTTP_202_ACCEPTED)

#         except Exception as e:
#             logger.error(f"RabbitMQ-ga ulana olmadi: {e}")
#             return Response({
#                 "error": "Tizim xatoligi (RabbitMQ ulanishda xato) 🔌"
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)