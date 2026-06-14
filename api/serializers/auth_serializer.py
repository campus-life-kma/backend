from rest_framework import serializers

from api.serializers.user_serializer import UserBaseSerializer


class DevLoginSerializer(serializers.Serializer):
    """Серіалізатор для локального входу розробника (Dev Login) через email."""

    email = serializers.EmailField(required=True, help_text="Пошта користувача")


class LoginSerializer(serializers.Serializer):
    """Серіалізатор входу через Microsoft Office 365 OAuth токен."""

    microsoft_access_token = serializers.CharField(
        required=True, help_text="Токен від microsoft після реєстрації через пошту"
    )


class LoginResponseSerializer(serializers.Serializer):
    """Серіалізатор відповіді успішного входу в систему, що містить JWT-токени."""

    access = serializers.CharField(help_text="Короткостроковий токен доступу (JWT)")
    refresh = serializers.CharField(help_text="Довгостроковий токен оновлення (JWT)")
    user = UserBaseSerializer(help_text="Базові дані авторизованого користувача")
