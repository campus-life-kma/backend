from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from api.models import Announcement, Floor, Room, TargetType, User
from api.serializers.user_serializer import UserMapSerializer


class AnnouncementSerializer(serializers.ModelSerializer):
    creator = UserMapSerializer(read_only=True, help_text="Автор оголошення")
    target_type = serializers.CharField(source="target_type.type", read_only=True, help_text="Тип аудиторії оголошення")
    target_floor_id = serializers.IntegerField(source="target_floor.id", read_only=True, allow_null=True)
    target_room_id = serializers.IntegerField(source="target_room.id", read_only=True, allow_null=True)
    target_user_ids = serializers.SerializerMethodField(help_text="ID користувачів, яким адресовано оголошення")

    class Meta:
        model = Announcement
        fields = [
            "id",
            "title",
            "message",
            "creator",
            "target_type",
            "target_floor_id",
            "target_room_id",
            "target_user_ids",
            "created_at",
            "expires_at",
            "is_pinned",
        ]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_target_user_ids(self, obj):
        return [str(user_id) for user_id in obj.target_users.values_list("id", flat=True)]


class AnnouncementCreateSerializer(serializers.Serializer):
    title = serializers.CharField(
        max_length=255,
        help_text="Короткий заголовок оголошення",
        error_messages={
            "blank": "Заголовок не може бути порожнім.",
            "required": "Вкажіть заголовок оголошення.",
            "max_length": "Заголовок не може бути довшим за 255 символів.",
        },
    )
    message = serializers.CharField(
        help_text="Повний текст оголошення",
        error_messages={
            "blank": "Текст оголошення не може бути порожнім.",
            "required": "Вкажіть текст оголошення.",
        },
    )
    target_type = serializers.SlugRelatedField(
        slug_field="type",
        queryset=TargetType.objects.all(),
        help_text="Тип аудиторії: GLOBAL, FLOOR, ROOM або SPECIFIC_USERS",
        error_messages={
            "does_not_exist": "Такого типу аудиторії не існує.",
            "invalid": "Некоректний тип аудиторії.",
            "required": "Вкажіть тип аудиторії оголошення.",
        },
    )
    target_floor = serializers.PrimaryKeyRelatedField(
        queryset=Floor.objects.all(),
        required=False,
        allow_null=True,
        help_text="ID поверху для оголошення типу FLOOR",
        error_messages={
            "does_not_exist": "Поверх з таким id не знайдено.",
            "incorrect_type": "ID поверху має бути числом.",
        },
    )
    target_room = serializers.PrimaryKeyRelatedField(
        queryset=Room.objects.all(),
        required=False,
        allow_null=True,
        help_text="ID кімнати для оголошення типу ROOM",
        error_messages={
            "does_not_exist": "Кімнату з таким id не знайдено.",
            "incorrect_type": "ID кімнати має бути числом.",
        },
    )
    target_users = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        required=False,
        help_text="Список ID користувачів для оголошення типу SPECIFIC_USERS",
        error_messages={
            "does_not_exist": "Користувача з таким id не знайдено.",
            "incorrect_type": "ID користувача має бути UUID.",
        },
    )
    expires_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Час, після якого оголошення стане неактивним",
        error_messages={
            "invalid": "Некоректний формат дати завершення.",
        },
    )
    is_pinned = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Чи закріпити оголошення зверху списку",
    )

    def validate(self, attrs):
        target_type = attrs["target_type"].type
        target_floor = attrs.get("target_floor")
        target_room = attrs.get("target_room")
        target_users = attrs.get("target_users", [])

        if target_type == "FLOOR" and not target_floor:
            raise serializers.ValidationError({"target_floor": "Для оголошення на поверх необхідно обрати поверх."})

        if target_type == "ROOM" and not target_room:
            raise serializers.ValidationError({"target_room": "Для оголошення на кімнату необхідно обрати кімнату."})

        if target_type == "SPECIFIC_USERS" and not target_users:
            raise serializers.ValidationError(
                {"target_users": "Для адресного оголошення необхідно обрати хоча б одного користувача."}
            )

        return attrs
