from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from api.models import Floor, Resource, Room, User
from api.serializers.socials_serializer import SocialEventMapSerializer
from api.serializers.user_serializer import UserMapSerializer


class FloorListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Floor
        fields = ["id", "number"]


class RoomBlockSerializer(serializers.ModelSerializer):
    floor_id = serializers.IntegerField(source="floor.id", read_only=True, help_text="ID поверху кімнати")
    room_type = serializers.CharField(source="room_type.type", read_only=True, help_text="Тип кімнати")

    class Meta:
        model = Room
        fields = ["id", "name", "floor_id", "room_type", "max_person", "is_blocked"]


class ResourceSerializer(serializers.ModelSerializer):
    resource_type = serializers.CharField(
        source="resource_type.type", help_text="Категорія ресурсу (наприклад 'Пралка', 'Духова піч')"
    )

    resource_icon = serializers.FileField(
        source="resource_type.icon_file", read_only=True, help_text="Іконка категорії ресурсу"
    )

    class Meta:
        model = Resource
        fields = ["id", "name", "max_person", "is_blocked", "resource_type", "resource_icon"]


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

    @extend_schema_field(UserMapSerializer(many=True))
    def get_current_users(self, obj):
        now = timezone.now()

        condition_present_here = Q(presences__room=obj, presences__expires_at__gt=now)
        condition_lives_here_and_idle = Q(room=obj) & ~Q(presences__expires_at__gt=now)

        users = User.objects.filter(condition_present_here | condition_lives_here_and_idle).distinct()
        return UserMapSerializer(users, many=True, context=self.context).data

    @extend_schema_field(SocialEventMapSerializer(many=True))
    def get_active_events(self, obj):
        now = timezone.now()
        events = obj.events.filter(status__status="ACTIVE", start_time__lte=now, end_time__gte=now).select_related(
            "creator", "status"
        )
        return SocialEventMapSerializer(events, many=True, context=self.context).data


class FloorMapDataSerializer(serializers.ModelSerializer):
    dormitory_name = serializers.CharField(
        source="dormitory.name", help_text="Офіційна назва гуртожитку (наприклад, 'Гуртожиток №3')"
    )
    rooms = RoomMapSerializer(many=True, read_only=True, help_text="Кімнати цього поверху")
    active_floor_events = serializers.SerializerMethodField(help_text="Івенти, які зараз проходять на поверху")

    class Meta:
        model = Floor
        fields = ["id", "number", "map_file", "dormitory_name", "notice", "rooms", "active_floor_events"]

    @extend_schema_field(SocialEventMapSerializer(many=True))
    def get_active_floor_events(self, obj):
        now = timezone.now()
        events = obj.events.filter(status__status="ACTIVE", start_time__lte=now, end_time__gte=now).select_related(
            "creator", "status"
        )
        return SocialEventMapSerializer(events, many=True, context=self.context).data


class RoomUpdateSerializer(serializers.ModelSerializer):
    room_type = serializers.PrimaryKeyRelatedField(
        queryset=Room.room_type.field.related_model.objects.all(), required=False
    )

    class Meta:
        model = Room
        fields = ["name", "room_type", "max_person", "is_blocked"]

    def validate_name(self, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise serializers.ValidationError("Назва не може бути порожньою.")
        return value

    def validate_max_person(self, value):
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError("Місткість кімнати має бути в межах від 0 до 100 осіб.")
        return value


class RoomCreateSerializer(serializers.ModelSerializer):
    room_type = serializers.PrimaryKeyRelatedField(
        queryset=Room.room_type.field.related_model.objects.all(),
        help_text="ID типу кімнати",
        error_messages={
            "does_not_exist": "Тип кімнати не знайдено.",
            "incorrect_type": "Некоректний тип значення для типу кімнати.",
            "required": "Оберіть тип кімнати.",
        },
    )
    name = serializers.CharField(
        max_length=100,
        help_text="Назва або номер кімнати",
        error_messages={
            "blank": "Вкажіть назву кімнати.",
            "max_length": "Назва кімнати занадто довга.",
            "required": "Вкажіть назву кімнати.",
        },
    )
    svg_element_id = serializers.CharField(
        max_length=100,
        help_text="ID неактивної кімнати з SVG-мапи поверху",
        error_messages={
            "blank": "Вкажіть ID кімнати на SVG-мапі.",
            "max_length": "ID кімнати на SVG-мапі занадто довгий.",
            "required": "Вкажіть ID кімнати на SVG-мапі.",
        },
    )

    class Meta:
        model = Room
        fields = ["name", "room_type", "max_person", "is_blocked", "svg_element_id"]
        extra_kwargs = {
            "max_person": {
                "help_text": "Максимальна місткість кімнати",
                "error_messages": {
                    "invalid": "Місткість має бути числом.",
                    "min_value": "Місткість не може бути меншою за 0.",
                    "required": "Вкажіть місткість кімнати.",
                },
            },
            "is_blocked": {
                "help_text": "Чи має кімната бути одразу заблокованою",
            },
        }

    def validate_name(self, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise serializers.ValidationError("Вкажіть назву кімнати.")
        return value

    def validate_max_person(self, value):
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError("Місткість кімнати має бути в межах від 0 до 100 осіб.")
        return value


class ResourceCreateUpdateSerializer(serializers.ModelSerializer):
    resource_type = serializers.PrimaryKeyRelatedField(
        queryset=Resource.resource_type.field.related_model.objects.all(), required=False
    )

    class Meta:
        model = Resource
        fields = ["name", "max_person", "is_blocked", "resource_type"]

    def validate_name(self, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise serializers.ValidationError("Вкажіть назву ресурсу.")
        return value

    def validate_max_person(self, value):
        if value is not None and (value < 1 or value > 100):
            raise serializers.ValidationError("Місткість ресурсу повинна бути в межах від 1 до 100 осіб.")
        return value
