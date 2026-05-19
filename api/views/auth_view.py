from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample, extend_schema_view

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from api.serializers.auth_serializer import DevLoginSerializer, LoginResponseSerializer, LoginSerializer
from api.services.auth_service import DevLoginService, LoginService


class DevLoginView(APIView):

    permission_classes = []

    @extend_schema(
        tags=["Авторизація"],
        summary="Логін для розробників",
        auth=[],
        request=DevLoginSerializer,
        description="Ендпоінт для авторизації під час розробки за допомогою email.",
        examples=[
            OpenApiExample(
                "Приклад вхідних даних",
                value={"email": "user1@ukma.edu.ua"},
                request_only=True,
            )
        ],
        responses={
            200: OpenApiResponse(
                response=LoginResponseSerializer,
                description="Успішна авторизація розробника. Повертає JWT токени та профіль мешканця.",
                examples=[
                    OpenApiExample(
                        "Успішний логін",
                        value={
                            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIi...",
                            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaC...",
                            "user": {
                                "id": "db7a2164-5717-4562-b3fc-2c963f66afa6",
                                "email": "user1@ukma.edu.ua",
                                "role": "RESIDENT",
                                "full_name": "Коваленко Дмитро",
                                "floor_id": "3",
                                "dormitory_id": "1",
                                "photo": "/media/avatars/avatar_87fb51a6-5abd-4398-bd5f-7a15dfdafa2d.jpg",
                            },
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Помилка валідації (наприклад, неправильний формат пошти).",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Невірний формат пошти", value={"email": ["Введіть коректну адресу електронної пошти."]}
                    )
                ],
            ),
            403: OpenApiResponse(
                description="Доступ заборонено (спрацьовує на продакшені).",
                response=dict,
                examples=[
                    OpenApiExample("Помилка доступу", value={"detail": "Метод доступний тільки під час розробки."})
                ],
            ),
            404: OpenApiResponse(
                description="Користувача не знайдено або акаунт не активовано.",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Користувач не знайдений", value={"detail": "Користувача не знайдено або він не активований"}
                    )
                ],
            ),
        },
    )
    def post(self, request):
        if not settings.DEBUG:
            return Response({"detail": "Метод доступний тільки під час розробки."}, status=status.HTTP_403_FORBIDDEN)

        serializer = DevLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = DevLoginService()
        login_data = service.execute_login(serializer.validated_data["email"])

        if not login_data:
            return Response(
                {"detail": "Користувача не знайдено або він не активований"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(login_data, status=status.HTTP_200_OK)


class LoginView(APIView):
    permission_classes = []

    @extend_schema(
        tags=["Авторизація"],
        summary="Логін для користувачів",
        auth=[],
        request=LoginSerializer,
        description="Ендпоінт для авторизації за допомогою SSO через корпоративну пошту.",
        examples=[
            OpenApiExample(
                "Приклад вхідних даних",
                value={"microsoft_access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Imti..."},
                request_only=True,
            )
        ],
        responses={
            200: OpenApiResponse(
                response=LoginResponseSerializer,
                description="Успішна авторизація через Microsoft SSO. Повертає токени та заповнений профіль.",
                examples=[
                    OpenApiExample(
                        "Успішний логін",
                        value={
                            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIi...",
                            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaC...",
                            "user": {
                                "id": "db7a2164-5717-4562-b3fc-2c963f66afa6",
                                "email": "user1@ukma.edu.ua",
                                "role": "RESIDENT",
                                "full_name": "Коваленко Дмитро",
                                "floor_id": "3",
                                "dormitory_id": "1",
                                "photo": "/media/avatars/avatar_87fb51a6-5abd-4398-bd5f-7a15dfdafa2d.jpg",
                            },
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Помилка валідації (наприклад, неправильний формат токена).",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Невірний формат токена", value={"microsoft_access_token": ["Введіть коректний токен."]}
                    )
                ],
            ),
            404: OpenApiResponse(
                description="Користувача не знайдено.",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Користувач не знайдений",
                        value={
                            "detail": "Користувача не знайдено або не вдалося активувати, "
                            "зверніться за допомогою до адміністрації"
                        },
                    )
                ],
            ),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = LoginService()
        login_data = service.execute_login(serializer.validated_data["microsoft_access_token"])

        if not login_data:
            return Response(
                {
                    "detail": "Користувача не знайдено або не вдалося активувати, "
                    "зверніться за допомогою до адміністрації"
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(login_data, status=status.HTTP_200_OK)


@extend_schema_view(
    post=extend_schema(
        tags=["Авторизація"],
        summary="Оновлення токена доступу (Refresh)",
        description="Приймає дійсний довгостроковий refresh токен та повертає новий короткостроковий access токен.",
        examples=[
            OpenApiExample(
                "Приклад вхідних даних",
                value={"refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaC..."},
                request_only=True,
            )
        ],
        responses={
            200: OpenApiResponse(
                response=dict,
                description="Токен успішно оновлено.",
                examples=[
                    OpenApiExample(
                        "Новий Access токен",
                        value={
                            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIi...",
                            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaC...",
                        },
                    )
                ],
            ),
            401: OpenApiResponse(
                description="Refresh токен недійсний або його термін дії закінчився.",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Токен недійсний", value={"detail": "Token is invalid or expired", "code": "token_not_valid"}
                    )
                ],
            ),
        },
    )
)
class CustomTokenRefreshView(TokenRefreshView):
    pass
