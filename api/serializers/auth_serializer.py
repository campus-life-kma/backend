from rest_framework import serializers

from api.serializers.user_serializer import UserBaseSerializer


class DevLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, help_text="Пошта користувача")


class LoginSerializer(serializers.Serializer):
    microsoft_access_token = serializers.CharField(
        required=True, help_text="Токен від microsoft після реєстрації через пошту"
    )


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField(help_text="Короткостроковий токен доступу (JWT)")
    refresh = serializers.CharField(help_text="Довгостроковий токен оновлення (JWT)")
    user = UserBaseSerializer(help_text="Базові дані авторизованого користувача")
