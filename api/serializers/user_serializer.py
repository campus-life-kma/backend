from rest_framework import serializers

from api.models import User


class UserBaseSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="role.name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "role",
            "name",
            "surname",
            "room",
            "photo",
        ]
