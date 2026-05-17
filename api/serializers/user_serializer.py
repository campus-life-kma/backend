from rest_framework import serializers

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
