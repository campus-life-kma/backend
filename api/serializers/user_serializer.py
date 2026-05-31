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


class UserFullSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    role_name = serializers.CharField(
        source="role.name", read_only=True, help_text="Системна роль, яка визначає рівень доступу до функцій платформи"
    )

    dormitory_name = serializers.CharField(
        source="room.floor.dormitory.name", read_only=True, help_text="Назва гуртожитку де живе користувач"
    )
    floor_number = serializers.CharField(
        source="room.floor.number", read_only=True, help_text="Номер поверху де живе користувач"
    )
    room_name = serializers.CharField(
        source="room.name", read_only=True, help_text="Номер або назва кімнати (наприклад, '314', '41/3')"
    )

    faculty_name = serializers.CharField(
        source="major.faculty.name",
        read_only=True,
        help_text="Повна назва факультету (наприклад, Факультет інформатики)",
    )
    major_name = serializers.CharField(
        source="major.name",
        read_only=True,
        help_text="Тільки назва спеціальності (наприклад, Інженерія програмного забезпечення)",
    )

    class Meta:
        model = User
        fields = [
            "id",
            "role_name",
            "display_name",
            "email",
            "photo",
            "dormitory_name",
            "floor_number",
            "room_name",
            "faculty_name",
            "major_name",
            "year",
            "status",
            "bio",
        ]

    @extend_schema_field(serializers.CharField)
    def get_display_name(self, obj):
        if obj.is_activated and obj.full_name:
            return obj.full_name
        return "Новий мешканець"


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["full_name", "photo", "status", "bio"]


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "role",
            "full_name",
            "email",
            "photo",
            "room",
            "major",
            "year",
            "status",
            "bio",
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
