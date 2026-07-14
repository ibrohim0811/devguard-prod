from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from rest_framework.fields import CharField


from .validations import validate_phone_number, validate_email  
from .models import Users, WebApplications, TransactionHistory


class RegisterSerializer(ModelSerializer):
    password = CharField(write_only=True, min_length=6)

    class Meta:
        model = Users
        fields = ('full_name', 'phone_number', 'email', 'password') 

    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        email = attrs.get('email')
        
        if not validate_phone_number(phone_number):
            raise serializers.ValidationError({"phone_number": "Telefon raqam formati xato!"})
        if not validate_email(email):
            raise serializers.ValidationError({"email": "Email formati xato!"})
        
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
