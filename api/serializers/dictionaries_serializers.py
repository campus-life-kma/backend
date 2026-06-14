from rest_framework import serializers

from api.models import Faculty, Major, Role, TargetType, Dormitory, Floor, Room, Resource


class FacultyListSerializer(serializers.ModelSerializer):
    """Серіалізатор для списку факультетів."""

    class Meta:
        model = Faculty
        fields = ["id", "name"]


class MajorListSerializer(serializers.ModelSerializer):
    """Серіалізатор для списку спеціальностей."""

    class Meta:
        model = Major
        fields = ["id", "name", "faculty"]


class RoleListSerializer(serializers.ModelSerializer):
    """Серіалізатор для списку ролей."""

    class Meta:
        model = Role
        fields = ["id", "name"]


class TargetTypeListSerializer(serializers.ModelSerializer):
    """Серіалізатор для списку типів цільової аудиторії оголошень."""

    class Meta:
        model = TargetType
        fields = ["id", "type"]


class DormitoryListSerializer(serializers.ModelSerializer):
    """Серіалізатор для списку гуртожитків."""

    class Meta:
        model = Dormitory
        fields = ["id", "name"]


class FloorListSerializer(serializers.ModelSerializer):
    """Серіалізатор для списку поверхів."""

    class Meta:
        model = Floor
        fields = ["id", "number", "dormitory"]


class RoomListSerializer(serializers.ModelSerializer):
    """Серіалізатор для списку кімнат, що повертає також кількість мешканців."""

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


class RoomTypeListSerializer(serializers.ModelSerializer):
    """Серіалізатор для словника типів кімнат."""

    class Meta:
        model = Room.room_type.field.related_model
        fields = ["id", "type"]


class ResourceTypeListSerializer(serializers.ModelSerializer):
    """Серіалізатор для словника типів ресурсів."""

    class Meta:
        model = Resource.resource_type.field.related_model
        fields = ["id", "type", "icon_file"]
