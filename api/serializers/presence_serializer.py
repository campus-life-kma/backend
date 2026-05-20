from rest_framework import serializers

from api.models import Presence


class PresenceCheckInSerializer(serializers.Serializer):
    room_id = serializers.IntegerField(min_value=1, required=True, help_text="Room id where the user checks in")


class PresenceResponseSerializer(serializers.ModelSerializer):
    room_id = serializers.IntegerField(read_only=True)
    room_name = serializers.CharField(source="room.name", read_only=True)
    floor_id = serializers.IntegerField(source="room.floor.id", read_only=True)

    class Meta:
        model = Presence
        fields = ["id", "room_id", "room_name", "floor_id", "joined_at", "expires_at"]
