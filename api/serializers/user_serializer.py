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
    role_id = serializers.IntegerField(
        source="role.id", read_only=True, allow_null=True, help_text="ID ролі користувача"
    )
    room_id = serializers.IntegerField(
        source="room.id", read_only=True, allow_null=True, help_text="ID кімнати проживання"
    )
    floor_id = serializers.IntegerField(
        source="room.floor.id", read_only=True, allow_null=True, help_text="ID поверху проживання"
    )
    major_id = serializers.IntegerField(
        source="major.id", read_only=True, allow_null=True, help_text="ID спеціальності"
    )
    faculty_id = serializers.IntegerField(
        source="faculty.id", read_only=True, allow_null=True, help_text="ID факультету (для викладачів)"
    )

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

    faculty_name = serializers.SerializerMethodField(
        help_text="Повна назва факультету (наприклад, Факультет інформатики)"
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
            "role_id",
            "role_name",
            "display_name",
            "email",
            "photo",
            "room_id",
            "floor_id",
            "major_id",
            "faculty_id",
            "dormitory_name",
            "floor_number",
            "room_name",
            "faculty_name",
            "major_name",
            "position",
            "education_level",
            "year",
            "status",
            "bio",
        ]

    @extend_schema_field(serializers.CharField)
    def get_display_name(self, obj):
        if obj.is_activated and obj.full_name:
            return obj.full_name
        return "Новий мешканець"

    @extend_schema_field(serializers.CharField)
    def get_faculty_name(self, obj):
        if obj.position == User.Position.TEACHER and obj.faculty:
            return obj.faculty.name
        if obj.position == User.Position.STUDENT and obj.major:
            return obj.major.faculty.name
        return None


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["full_name", "photo", "status", "bio"]


class ModeratorUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["status", "bio"]


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
            "faculty",
            "position",
            "education_level",
            "year",
            "status",
            "bio",
        ]

        extra_kwargs = {
            "education_level": {
                "help_text": "Рівень навчання: BACHELOR, MASTER або PHD.",
                "error_messages": {
                    "invalid_choice": "Оберіть коректний рівень навчання: BACHELOR, MASTER або PHD.",
                },
            },
            "year": {
                "help_text": "Курс або рік навчання. Для бакалавра: 1-4, для магістра: 1-2, для аспіранта: 1-4.",
                "error_messages": {
                    "invalid": "Курс або рік навчання має бути числом.",
                },
            },
        }

    def validate(self, attrs):
        position = attrs.get("position", getattr(self.instance, "position", User.Position.STUDENT))

        # Якщо користувач не студент, ми ігноруємо education_level та year, а також major
        if position != User.Position.STUDENT:
            if "education_level" in attrs:
                attrs["education_level"] = None
            if "year" in attrs:
                attrs["year"] = None
            if "major" in attrs:
                attrs["major"] = None

            # Якщо працівник, він не має і факультету
            if position == User.Position.EMPLOYEE and "faculty" in attrs:
                attrs["faculty"] = None

            return attrs

        education_level = attrs.get("education_level", getattr(self.instance, "education_level", None))
        year = attrs.get("year", getattr(self.instance, "year", None))

        if year is None:
            return attrs

        if education_level == User.EducationLevel.MASTER and year not in (1, 2):
            raise serializers.ValidationError({"year": ["Для магістратури можна вказати лише 1 або 2 курс."]})

        if education_level in (User.EducationLevel.BACHELOR, User.EducationLevel.PHD) and year not in (1, 2, 3, 4):
            raise serializers.ValidationError({"year": ["Для цього рівня навчання можна вказати значення від 1 до 4."]})

        return attrs


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


class AnnouncementRecipientSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField(help_text="Ім'я користувача для списку адресатів")
    role_name = serializers.CharField(source="role.name", read_only=True, allow_null=True, help_text="Роль користувача")
    floor_id = serializers.IntegerField(source="room.floor.id", read_only=True, allow_null=True, help_text="ID поверху")
    floor_number = serializers.IntegerField(
        source="room.floor.number", read_only=True, allow_null=True, help_text="Номер поверху"
    )
    room_id = serializers.IntegerField(source="room.id", read_only=True, allow_null=True, help_text="ID кімнати")
    room_name = serializers.CharField(source="room.name", read_only=True, allow_null=True, help_text="Назва кімнати")
    faculty_name = serializers.SerializerMethodField(help_text="Назва факультету")
    major_name = serializers.CharField(
        source="major.name", read_only=True, allow_null=True, help_text="Назва спеціальності"
    )

    class Meta:
        model = User
        fields = [
            "id",
            "display_name",
            "email",
            "role_name",
            "floor_id",
            "floor_number",
            "room_id",
            "room_name",
            "faculty_name",
            "major_name",
            "year",
        ]

    @extend_schema_field(serializers.CharField)
    def get_display_name(self, obj):
        if obj.full_name:
            return obj.full_name
        return obj.email

    @extend_schema_field(serializers.CharField)
    def get_faculty_name(self, obj):
        if obj.position == User.Position.TEACHER and obj.faculty:
            return obj.faculty.name
        if obj.position == User.Position.STUDENT and obj.major:
            return obj.major.faculty.name
        return None
