from datetime import timedelta
from django.utils import timezone

from rest_framework import serializers

from api.models import Booking, Resource
from api.serializers.user_serializer import UserMapSerializer


class BookingCreateSerializer(serializers.Serializer):
    """Серіалізатор для створення нового бронювання ресурсу з бізнес-валідацією тривалості."""

    max_booking_duration = timedelta(hours=3)
    max_booking_advance = timedelta(days=30)

    resource = serializers.PrimaryKeyRelatedField(
        queryset=Resource.objects.all(),
        help_text="ID ресурсу, який потрібно забронювати",
        error_messages={
            "does_not_exist": "Ресурс з таким id не знайдено.",
            "incorrect_type": "ID ресурсу має бути числом.",
            "required": "Вкажіть ресурс для бронювання.",
        },
    )
    start_time = serializers.DateTimeField(
        help_text="Час початку бронювання",
        error_messages={
            "invalid": "Некоректний формат часу початку бронювання.",
            "required": "Вкажіть час початку бронювання.",
        },
    )
    end_time = serializers.DateTimeField(
        help_text="Час завершення бронювання. Максимальна тривалість бронювання - 3 години",
        error_messages={
            "invalid": "Некоректний формат часу завершення бронювання.",
            "required": "Вкажіть час завершення бронювання.",
        },
    )

    def validate(self, attrs):
        """Перевіряє коректність часових рамок бронювання."""
        now = timezone.now()

        if attrs["start_time"] < now:
            raise serializers.ValidationError({"start_time": "Не можна створювати бронювання в минулому."})

        if attrs["end_time"] <= attrs["start_time"]:
            raise serializers.ValidationError({"end_time": "Час завершення має бути пізніше часу початку."})

        # Обмеження на максимальну тривалість бронювання (3 години)
        if attrs["end_time"] - attrs["start_time"] > self.max_booking_duration:
            raise serializers.ValidationError({"end_time": "Бронювання не може тривати довше 3 годин."})

        # Бронювання не більше ніж на 30 днів вперед
        if attrs["start_time"] > now + self.max_booking_advance:
            raise serializers.ValidationError(
                {"start_time": "Не можна створювати бронювання більше ніж на 30 днів уперед."}
            )

        return attrs


class BookingSerializer(serializers.ModelSerializer):
    """Детальний серіалізатор для виведення інформації про бронювання."""

    user = UserMapSerializer(read_only=True, help_text="Користувач, який створив бронювання")
    cancelled_by = UserMapSerializer(read_only=True, help_text="Користувач, який скасував бронювання")
    resource_id = serializers.IntegerField(source="resource.id", read_only=True, help_text="ID ресурсу")
    resource_name = serializers.CharField(source="resource.name", read_only=True, help_text="Назва ресурсу")
    room_id = serializers.IntegerField(source="resource.room.id", read_only=True, help_text="ID кімнати ресурсу")
    room_name = serializers.CharField(source="resource.room.name", read_only=True, help_text="Назва кімнати ресурсу")
    floor_id = serializers.IntegerField(source="resource.room.floor.id", read_only=True, help_text="ID поверху ресурсу")
    status = serializers.CharField(source="status.status", read_only=True, help_text="Статус бронювання")

    class Meta:
        model = Booking
        fields = [
            "id",
            "user",
            "cancelled_by",
            "resource_id",
            "resource_name",
            "room_id",
            "room_name",
            "floor_id",
            "start_time",
            "end_time",
            "status",
        ]


class BookingUpdateSerializer(serializers.Serializer):
    """Серіалізатор для оновлення часу існуючого бронювання."""

    max_booking_duration = timedelta(hours=3)
    max_booking_advance = timedelta(days=30)

    start_time = serializers.DateTimeField(
        help_text="Новий час початку", error_messages={"required": "Вкажіть новий час початку."}
    )
    end_time = serializers.DateTimeField(
        help_text="Новий час завершення", error_messages={"required": "Вкажіть новий час завершення."}
    )

    def validate(self, attrs):
        """Валідує новий часовий діапазон бронювання."""
        now = timezone.now()

        if attrs["start_time"] < now:
            raise serializers.ValidationError({"start_time": "Не можна перенести бронювання на минулий час."})

        if attrs["end_time"] <= attrs["start_time"]:
            raise serializers.ValidationError({"end_time": "Час завершення має бути пізніше часу початку."})

        if attrs["end_time"] - attrs["start_time"] > self.max_booking_duration:
            raise serializers.ValidationError({"end_time": "Бронювання не може тривати довше 3 годин."})

        if attrs["start_time"] > now + self.max_booking_advance:
            raise serializers.ValidationError(
                {"start_time": "Не можна переносити бронювання більше ніж на 30 днів уперед."}
            )

        return attrs


class ResourceScheduleSerializer(serializers.ModelSerializer):
    """Полегшений серіалізатор для виведення розкладу бронювань ресурсу."""

    booking_id = serializers.IntegerField(source="id", read_only=True, help_text="ID бронювання")
    status = serializers.CharField(source="status.status", read_only=True, help_text="Статус бронювання")
    user = UserMapSerializer(read_only=True, help_text="Користувач, який створив бронювання")

    class Meta:
        model = Booking
        fields = ["booking_id", "start_time", "end_time", "status", "user"]


class ResourceBlockSerializer(serializers.ModelSerializer):
    """Серіалізатор блокування/розблокування та виведення деталей ресурсу."""

    room_id = serializers.IntegerField(source="room.id", read_only=True, help_text="ID кімнати ресурсу")
    room_name = serializers.CharField(source="room.name", read_only=True, help_text="Назва кімнати ресурсу")

    class Meta:
        model = Resource
        fields = ["id", "name", "room_id", "room_name", "max_person", "is_blocked"]
