from rest_framework import serializers

from api.models import Presence


class PresenceCheckInSerializer(serializers.Serializer):
    """Серіалізатор для вхідних даних реєстрації присутності."""

    room_id = serializers.IntegerField(
        min_value=1,
        required=True,
        help_text="ID кімнати, у якій користувач відмічає присутність",
        error_messages={
            "required": "Вкажіть ID кімнати.",
            "invalid": "ID кімнати має бути числом.",
            "min_value": "ID кімнати має бути додатним числом.",
        },
    )


class PresenceResponseSerializer(serializers.ModelSerializer):
    """Серіалізатор представлення активного запису присутності користувача."""

    room_id = serializers.IntegerField(read_only=True, help_text="ID кімнати, у якій відмічено присутність")
    room_name = serializers.CharField(source="room.name", read_only=True, help_text="Назва кімнати")
    floor_id = serializers.IntegerField(source="room.floor.id", read_only=True, help_text="ID поверху кімнати")

    class Meta:
        model = Presence
        fields = ["id", "room_id", "room_name", "floor_id", "joined_at", "expires_at"]
