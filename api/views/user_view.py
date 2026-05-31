from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiExample
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import User
from api.serializers.user_serializer import UserFullSerializer


class GetUserView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Користувач"],
        summary="Отримати дані про користувача",
        request=None,
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=OpenApiTypes.UUID,
                location="path",
                required=True,
                description="Id користувача, про якого ми хочемо дізнатися інформацію",
                examples=[OpenApiExample(name="Користувач 1", value="906fb366-a8db-4f14-9ab4-00e5869c21fa")],
            )
        ],
        description="Ендпоінт для отримання користувача за його id",
        responses={
            200: OpenApiResponse(
                response=UserFullSerializer,
                description="Успішне отримання користувача",
                examples=[
                    OpenApiExample(
                        name="Користувач",
                        value={
                            "id": "906fb366-a8db-4f14-9ab4-00e5869c21fa",
                            "role_name": "RESIDENT",
                            "display_name": "Коваленко Дмитро",
                            "email": "user1@ukma.edu.ua",
                            "photo": "http://localhost:8888/media/avatars/avatar_87fb51a6-5abd-4398-bd5f-7a15dfdafa2d.jpg",
                            "dormitory_name": "Маккейна",
                            "floor_number": "4",
                            "room_name": "41/2",
                            "faculty_name": "Тестовий факультет",
                            "major_name": "Тестова спеціальність",
                            "year": "4",
                            "status": "Вчуся",
                            "bio": "Працюю над проєктами та дедлайнами.",
                        }
                    )
                ]
            ),
            401: OpenApiResponse(
                description="Не авторизовано (відсутній або недійсний токен).",
                response=dict,
                examples=[OpenApiExample("Помилка авторизації", value={"detail": "Дані авторизації не надані!."})],
            ),
            404: OpenApiResponse(
                description="Користувача не знайдено.",
                response=dict,
                examples=[OpenApiExample("Користувач відсутній", value={"detail": "Користувача з таким id не знайдено!"})],
            )
        }
    )
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            serializer = UserFullSerializer(user)

            return Response(serializer.data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)