from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from api.models import User


class UserBaseSerializer(serializers.ModelSerializer):
    role = serializers.CharField(
        source="role.name", read_only=True, help_text="Системна роль, яка визначає рівень доступу до функцій платформи"
    )
    floor_id = serializers.CharField(source="room.floor.id", read_only=True, help_text="id поверху де живе користувач")
    dormitory_id = serializers.CharField(
        source="room.floor.dormitory.id", read_only=True, help_text="id гуртожитку де живе користувач"
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "role",
            "full_name",
            "floor_id",
            "dormitory_id",
            "photo",
        ]


class UserMapSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "display_name", "photo"]

    @extend_schema_field(serializers.CharField)
    def get_display_name(self, obj):
        if obj.is_activated and obj.full_name:
            return obj.full_name
        return "Новий мешканець"
