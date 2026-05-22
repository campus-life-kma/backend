from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers.bookings_serializer import (
    BookingCreateSerializer,
    BookingSerializer,
    ResourceBlockSerializer,
    ResourceScheduleSerializer,
)
from api.services.bookings_service import BookingsService


def get_booking_error_status(error_message):
    if "не знайдено" in error_message:
        return status.HTTP_404_NOT_FOUND

    if "немає прав" in error_message or "Тільки адміністратор" in error_message:
        return status.HTTP_403_FORBIDDEN

    return status.HTTP_400_BAD_REQUEST


class ResourceScheduleView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Бронювання"],
        summary="Отримання розкладу ресурсу",
        responses={
            200: OpenApiResponse(
                response=ResourceScheduleSerializer(many=True),
                description="Зайняті слоти ресурсу на сьогодні та завтра отримано.",
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            404: OpenApiResponse(description="Ресурс не знайдено."),
        },
    )
    def get(self, request, resource_id):
        service = BookingsService()

        try:
            bookings = service.get_resource_schedule(resource_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=get_booking_error_status(str(exc)))

        serializer = ResourceScheduleSerializer(bookings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BookingCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Бронювання"],
        summary="Створення бронювання",
        request=BookingCreateSerializer,
        responses={
            201: OpenApiResponse(response=BookingSerializer, description="Бронювання успішно створено."),
            400: OpenApiResponse(description="Бронювання неможливо створити."),
            401: OpenApiResponse(description="Користувач не авторизований."),
            404: OpenApiResponse(description="Ресурс не знайдено."),
        },
    )
    def post(self, request):
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = BookingsService()

        try:
            booking = service.create_booking(request.user, serializer.validated_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=get_booking_error_status(str(exc)))

        response_serializer = BookingSerializer(booking, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class MyBookingsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Бронювання"],
        summary="Отримання моїх активних бронювань",
        responses={
            200: OpenApiResponse(
                response=BookingSerializer(many=True),
                description="Майбутні та активні бронювання користувача отримано.",
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
        },
    )
    def get(self, request):
        service = BookingsService()
        bookings = service.get_my_bookings(request.user)
        serializer = BookingSerializer(bookings, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class BookingCancelView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Бронювання"],
        summary="Скасування бронювання",
        request=None,
        responses={
            200: OpenApiResponse(response=BookingSerializer, description="Бронювання скасовано."),
            401: OpenApiResponse(description="Користувач не авторизований."),
            403: OpenApiResponse(description="Недостатньо прав для скасування бронювання."),
            404: OpenApiResponse(description="Бронювання не знайдено."),
        },
    )
    def patch(self, request, booking_id):
        service = BookingsService()

        try:
            booking = service.cancel_booking(request.user, booking_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=get_booking_error_status(str(exc)))

        serializer = BookingSerializer(booking, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResourceBlockView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Бронювання"],
        summary="Блокування ресурсу",
        request=None,
        responses={
            200: OpenApiResponse(description="Ресурс заблоковано."),
            401: OpenApiResponse(description="Користувач не авторизований."),
            403: OpenApiResponse(description="Тільки адміністратор може блокувати ресурси."),
            404: OpenApiResponse(description="Ресурс не знайдено."),
        },
    )
    def patch(self, request, resource_id):
        service = BookingsService()

        try:
            resource, cancelled_count = service.block_resource(request.user, resource_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=get_booking_error_status(str(exc)))

        serializer = ResourceBlockSerializer(resource, context={"request": request})
        return Response(
            {
                "resource": serializer.data,
                "cancelled_bookings_count": cancelled_count,
            },
            status=status.HTTP_200_OK,
        )


class ResourceUnblockView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Бронювання"],
        summary="Розблокування ресурсу",
        request=None,
        responses={
            200: OpenApiResponse(
                response=ResourceBlockSerializer,
                description="Ресурс розблоковано.",
                examples=[
                    OpenApiExample(
                        "Ресурс розблоковано",
                        value={
                            "id": 1,
                            "name": "Пральна машина 1",
                            "room_id": 2,
                            "room_name": "Пральня",
                            "max_person": 1,
                            "is_blocked": False,
                        },
                    )
                ],
            ),
            401: OpenApiResponse(description="Користувач не авторизований."),
            403: OpenApiResponse(description="Тільки адміністратор може розблоковувати ресурси."),
            404: OpenApiResponse(description="Ресурс не знайдено."),
        },
    )
    def patch(self, request, resource_id):
        service = BookingsService()

        try:
            resource = service.unblock_resource(request.user, resource_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=get_booking_error_status(str(exc)))

        serializer = ResourceBlockSerializer(resource, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
