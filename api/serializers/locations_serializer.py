from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from api.models import Floor, Resource, Room, User
from api.serializers.socials_serializer import SocialEventMapSerializer
from api.serializers.user_serializer import UserMapSerializer


class FloorListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Floor
        fields = ["id", "number"]


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ["id", "name", "max_person", "is_blocked"]


class RoomMapSerializer(serializers.ModelSerializer):
    room_type = serializers.CharField(
        source="room_type.type", help_text="Категорія приміщення (наприклад, 'Житлова', 'Кухня', 'Душова', 'Пральня')"
    )
    resources = ResourceSerializer(many=True, read_only=True, help_text="Ресурси в даній кімнаті")
    current_users = serializers.SerializerMethodField(help_text="Користувачі, які зараз знаходяться на поверху")
    active_events = serializers.SerializerMethodField(help_text="Івенти, які зараз проходять в кімнаті")

    class Meta:
        model = Room
        fields = [
            "id",
            "name",
            "room_type",
            "max_person",
            "is_blocked",
            "svg_element_id",
            "resources",
            "current_users",
            "active_events",
        ]

    def get_current_users(self, obj):
        now = timezone.now()

        condition_present_here = Q(presences__room=obj, presences__expires_at__gt=now)
        condition_lives_here_and_idle = Q(room=obj) & ~Q(presences__expires_at__gt=now)

        users = User.objects.filter(condition_present_here | condition_lives_here_and_idle).distinct()
        return UserMapSerializer(users, many=True, context=self.context).data

    def get_active_events(self, obj):
        now = timezone.now()
        events = obj.events.filter(start_time__lte=now, end_time__gte=now)
        return SocialEventMapSerializer(events, many=True, context=self.context).data


class FloorMapDataSerializer(serializers.ModelSerializer):
    dormitory_name = serializers.CharField(
        source="dormitory.name", help_text="Офіційна назва гуртожитку (наприклад, 'Гуртожиток №3')"
    )
    rooms = RoomMapSerializer(many=True, read_only=True, help_text="Кімнати цього поверху")
    active_floor_events = serializers.SerializerMethodField(help_text="Івенти, які зараз проходять на поверху")

    class Meta:
        model = Floor
        fields = ["id", "number", "map_file", "dormitory_name", "rooms", "active_floor_events"]

    def get_active_floor_events(self, obj):
        now = timezone.now()
        events = obj.events.filter(start_time__lte=now, end_time__gte=now)
        return SocialEventMapSerializer(events, many=True, context=self.context).data
