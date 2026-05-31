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
    class Meta:
        model = Room
        fields = ["id", "name", "floor"]
