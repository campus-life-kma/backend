from rest_framework import serializers

from api.models import Faculty, Major, Role, TargetType, Dormitory, Floor, Room


class FacultyListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = ["id", "name"]


class MajorListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Major
        fields = ["id", "name", "faculty"]


class RoleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name"]


class TargetTypeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = TargetType
        fields = ["id", "type"]


class DormitoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dormitory
        fields = ["id", "name"]


class FloorListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Floor
        fields = ["id", "number", "dormitory"]


class RoomListSerializer(serializers.ModelSerializer):
    floor_number = serializers.IntegerField(source="floor.number", read_only=True, help_text="Номер поверху")
    room_type = serializers.CharField(source="room_type.type", read_only=True, help_text="Тип кімнати")
    current_residents_count = serializers.IntegerField(
        read_only=True, help_text="Поточна кількість закріплених мешканців"
    )

    class Meta:
        model = Room
        fields = [
            "id",
            "name",
            "floor",
            "floor_number",
            "room_type",
            "max_person",
            "is_blocked",
            "current_residents_count",
        ]
