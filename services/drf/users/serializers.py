from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from rest_framework.fields import CharField
from rest_framework.validators import UniqueValidator


from .validations import validate_phone_number, validate_email  
from .models import Users, WebApplications, TransactionHistory, ScanHistory


from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

class RegisterSerializer(ModelSerializer):
    password = CharField(write_only=True, min_length=8)

    class Meta:
        model = Users
        fields = ('full_name', 'phone_number', 'email', 'password') 

    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        email = attrs.get('email')
        password = attrs.get('password')

        if not validate_phone_number(phone_number):
            raise serializers.ValidationError({"phone_number": "Telefon raqam formati xato!"})
        if not validate_email(email):
            raise serializers.ValidationError({"email": "Email formati xato!"})

        if password:
            try:
                validate_password(password)
            except DjangoValidationError as e:
                raise serializers.ValidationError({"password": list(e.messages)})
        
        if Users.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "Ushbu email allaqachon ro'yxatdan o'tgan!"})
        if Users.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError({"phone_number": "Ushbu telefon raqam allaqachon ro'yxatdan o'tgan!"})
  
        return attrs
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.update(instance.token())
        return data
    


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(max_length=6, min_length=6, required=True)



class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    


class ProfileSerializer(ModelSerializer):
    class Meta:
        model = Users
        fields = ["phone_number", "email", "full_name", "avatar"]
        read_only_fields = ["phone_number", "email"]




class WebApplicationsSerializer(serializers.ModelSerializer):
    domain = serializers.URLField(
        validators=[
            UniqueValidator(
                queryset=WebApplications.objects.all(),
                message="Ushbu domen tizimda allaqachon ro'yxatdan o'tgan! ⚠️"
            )
        ]
    )
    class Meta:
        model = WebApplications
        fields = [
            'id', 'user', 'domain', 'title', 'is_verified', 
            'verification_token', 'slug', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'is_verified', 'verification_token', 'created_at', 'slug']

    

    def to_representation(self, instance):
        data = super().to_representation(instance) 
        data.update(instance.verif_token())
        return data
    

class TransactionSerializer(ModelSerializer):
    class Meta:
        model = TransactionHistory
        fields = "__all__"
        read_only_fields = ["user", "webapp", "payment_id", "status", "payment_date"]


class CheckPaymentSerializer(serializers.Serializer):
    webapp_slug = serializers.CharField(required=True)


class StartScanSerializer(serializers.Serializer):
    slug = serializers.SlugField(
        required=True 
    )


class ScanHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model= ScanHistory
        fields = "__all__"
        read_only_fields = ("webapp", "scanned_at", "result_summary", "scan_type", "task_id")
