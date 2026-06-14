from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers.statistics_serializer import StatisticsSummarySerializer
from api.services.statistics_service import StatisticsService


class StatisticsSummaryView(APIView):
    """Представлення для отримання агрегованої статистики по гуртожитку."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Статистика"],
        summary="Отримати статистику для адміністратора або модератора",
        description=(
            "Повертає агреговану статистику Campus Life. Адміністратор бачить дані свого гуртожитку, "
            "а модератор бачить лише дані свого поверху. Звичайним мешканцям ендпоінт недоступний."
        ),
        responses={
            200: OpenApiResponse(
                response=StatisticsSummarySerializer,
                description="Статистику успішно отримано.",
                examples=[
                    OpenApiExample(
                        "Статистика адміністратора",
                        value={
                            "scope": {
                                "type": "DORMITORY",
                                "dormitory_name": "Маккейна",
                                "floor_id": None,
                                "floor_number": None,
                                "role": "ADMIN",
                            },
                            "residents": {
                                "total": 120,
                                "activated": 95,
                                "not_activated": 25,
                                "moderators": 9,
                            },
                            "rooms": {
                                "total": 80,
                                "living": 60,
                                "blocked": 2,
                                "full": 41,
                            },
                            "resources": {
                                "total": 18,
                                "blocked": 1,
                            },
                            "bookings": {
                                "active": 12,
                                "today": 5,
                                "cancelled": 7,
                                "cancelled_by_residents": 4,
                                "cancelled_by_moderators": 2,
                                "cancelled_by_admins": 1,
                                "top_resources": [
                                    {
                                        "resource_id": 3,
                                        "resource_name": "Пральна машина 1",
                                        "room_name": "Пральня",
                                        "floor_number": 4,
                                        "bookings_count": 14,
                                    }
                                ],
                            },
                            "social": {
                                "active_events": 6,
                                "cancelled_events": 2,
                                "active_sharing_requests": 8,
                                "completed_sharing_requests": 11,
                                "cancelled_sharing_requests": 1,
                                "floor_activity": [
                                    {
                                        "floor_id": 4,
                                        "floor_number": 4,
                                        "residents_count": 22,
                                        "active_events_count": 2,
                                        "active_sharing_requests_count": 3,
                                        "active_presence_count": 5,
                                    }
                                ],
                            },
                            "announcements": {
                                "active": 3,
                                "pinned": 1,
                                "total": 15,
                            },
                            "presence": {
                                "active": 5,
                            },
                        },
                    )
                ],
            ),
            401: OpenApiResponse(description="Не авторизовано."),
            403: OpenApiResponse(
                description="Статистика недоступна звичайному мешканцю.",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Брак прав",
                        value={"detail": "Статистика доступна лише адміністраторам і модераторам."},
                    )
                ],
            ),
        },
    )
    def get(self, request):
        """Повертає статистичний звіт для авторизованого адміністратора або модератора.

        Args:
            request: Об'єкт HTTP-запиту.

        Returns:
            Response: Дані звіту з кодом 200 OK.
        """
        summary = StatisticsService().get_summary(request.user)
        return Response(summary, status=status.HTTP_200_OK)
