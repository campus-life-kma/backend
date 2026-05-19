from rest_framework import serializers

from api.models import SocialEvent
from api.serializers.user_serializer import UserMapSerializer


class SocialEventMapSerializer(serializers.ModelSerializer):
    creator = UserMapSerializer(read_only=True, help_text="Організатор івенту")
    participants_count = serializers.SerializerMethodField(help_text="Кількість учасників")

    class Meta:
        model = SocialEvent
        fields = ["id", "title", "creator", "participants_count"]

    def get_participants_count(self, obj):
        return obj.participants.count()