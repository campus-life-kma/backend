from django.utils import timezone
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from api.models import Floor, Room, SocialEvent, SocialSharingRequest
from api.serializers.user_serializer import UserMapSerializer


class SocialEventMapSerializer(serializers.ModelSerializer):
    """Полегшений серіалізатор соціальної події для відображення на інтерактивній карті."""

    creator = UserMapSerializer(read_only=True, help_text="Організатор івенту")
    status = serializers.CharField(source="status.status", read_only=True, help_text="Поточний статус івенту")
    participants_count = serializers.SerializerMethodField(help_text="Кількість учасників")

    class Meta:
        model = SocialEvent
        fields = ["id", "title", "creator", "status", "participants_count"]

    @extend_schema_field(serializers.IntegerField)
    def get_participants_count(self, obj) -> int:
        """Повертає кількість учасників події (використовує анотацію за наявності)."""
        annotated_count = getattr(obj, "participants_count", None)
        if annotated_count is not None:
            return annotated_count

        return obj.participants.count()


class SocialEventCreateSerializer(serializers.ModelSerializer):
    """Серіалізатор для створення нової соціальної події."""

    room = serializers.PrimaryKeyRelatedField(
        queryset=Room.objects.all(),
        required=False,
        allow_null=True,
        help_text="ID кімнати, де відбудеться подія",
    )
    floor = serializers.PrimaryKeyRelatedField(
        queryset=Floor.objects.all(),
        required=False,
        allow_null=True,
        help_text="ID поверху, де відбудеться подія",
    )
    custom_location = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=255,
        help_text="Текстова назва місця, якщо подія не прив'язана до кімнати або поверху",
    )

    class Meta:
        model = SocialEvent
        fields = [
            "title",
            "description",
            "start_time",
            "end_time",
            "max_person",
            "is_faculty_only",
            "is_major_only",
            "room",
            "floor",
            "custom_location",
        ]
        extra_kwargs = {
            "title": {"help_text": "Назва події"},
            "description": {"help_text": "Опис події"},
            "start_time": {"help_text": "Час початку події"},
            "end_time": {"help_text": "Час завершення події"},
            "max_person": {"help_text": "Максимальна кількість учасників. Якщо 0, кількість не обмежена"},
            "is_faculty_only": {"help_text": "Чи доступна подія тільки студентам факультету автора"},
            "is_major_only": {"help_text": "Чи доступна подія тільки студентам спеціальності автора"},
        }

    def validate_custom_location(self, value: str) -> str | None:
        """Очищує кастомну назву локації від зайвих пробілів."""
        if value is None:
            return value

        value = value.strip()
        return value or None

    def validate(self, attrs):
        """Перевіряє коректність часу початку/завершення та наявність локації події."""
        now = timezone.now()

        if attrs["start_time"] < now:
            raise serializers.ValidationError({"start_time": "Час початку події не може быть в минулому."})

        if attrs["end_time"] <= attrs["start_time"]:
            raise serializers.ValidationError({"end_time": "Час завершення має бути пізніше часу початку."})

        if not attrs.get("room") and not attrs.get("floor") and not attrs.get("custom_location"):
            raise serializers.ValidationError(
                {"detail": "Вкажіть хоча б одну локацію: кімнату, поверх або текстову назву місця."}
            )

        return attrs


class SocialEventDetailSerializer(serializers.ModelSerializer):
    """Детальний серіалізатор для перегляду інформації про соціальну подію."""

    creator = UserMapSerializer(read_only=True, help_text="Автор події")
    status = serializers.CharField(source="status.status", read_only=True, help_text="Поточний статус івенту")
    participants_count = serializers.SerializerMethodField(help_text="Кількість учасників")
    room_id = serializers.IntegerField(source="room.id", read_only=True, allow_null=True)
    room_name = serializers.CharField(source="room.name", read_only=True, allow_null=True)
    floor_id = serializers.SerializerMethodField(help_text="ID поверху події")
    type = serializers.SerializerMethodField(help_text="Тип елемента стрічки")

    class Meta:
        model = SocialEvent
        fields = [
            "type",
            "id",
            "title",
            "description",
            "status",
            "start_time",
            "end_time",
            "created_at",
            "max_person",
            "is_faculty_only",
            "is_major_only",
            "creator",
            "participants_count",
            "room_id",
            "room_name",
            "floor_id",
            "custom_location",
        ]

    @extend_schema_field(serializers.CharField)
    def get_type(self, obj) -> str:
        return "event"

    @extend_schema_field(serializers.IntegerField)
    def get_participants_count(self, obj) -> int:
        annotated_count = getattr(obj, "participants_count", None)
        if annotated_count is not None:
            return annotated_count

        return obj.participants.count()

    @extend_schema_field(serializers.IntegerField)
    def get_floor_id(self, obj) -> int | None:
        """Повертає ID поверху події безпосередньо або через кімнату."""
        if obj.floor_id:
            return obj.floor_id

        if obj.room_id:
            return obj.room.floor_id

        return None


class SocialEventFullDetailSerializer(SocialEventDetailSerializer):
    """Розширений детальний серіалізатор події, що включає повний список учасників."""

    participants = UserMapSerializer(many=True, read_only=True, help_text="Список учасників події")

    class Meta(SocialEventDetailSerializer.Meta):
        fields = [field for field in SocialEventDetailSerializer.Meta.fields if field != "participants_count"] + [
            "participants"
        ]


class SocialSharingRequestCreateSerializer(serializers.ModelSerializer):
    """Серіалізатор для створення нового запиту на шеринг речей."""

    class Meta:
        model = SocialSharingRequest
        fields = ["title"]
        extra_kwargs = {
            "title": {"help_text": "Короткий опис речі або допомоги, яка потрібна"},
        }


class SocialSharingRequestDetailSerializer(serializers.ModelSerializer):
    """Детальний серіалізатор запиту на шеринг речей."""

    creator = UserMapSerializer(read_only=True, help_text="Автор запиту")
    status = serializers.CharField(source="status.status", read_only=True, help_text="Поточний статус запиту")
    type = serializers.SerializerMethodField(help_text="Тип елемента стрічки")
    floor_id = serializers.SerializerMethodField(help_text="ID поверху автора запиту")

    class Meta:
        model = SocialSharingRequest
        fields = ["type", "id", "title", "creator", "status", "created_at", "floor_id"]

    @extend_schema_field(serializers.CharField)
    def get_type(self, obj) -> str:
        return "sharing_request"

    @extend_schema_field(serializers.IntegerField)
    def get_floor_id(self, obj) -> int | None:
        if obj.creator.room_id:
            return obj.creator.room.floor_id

        return None


class SocialEventFeedSerializer(serializers.ModelSerializer):
    """Серіалізатор події для відображення в загальній стрічці активностей."""

    creator = UserMapSerializer(read_only=True, help_text="Автор події")
    status = serializers.CharField(source="status.status", read_only=True, help_text="Поточний статус івенту")
    type = serializers.SerializerMethodField(help_text="Тип елемента стрічки")

    is_faculty_only = serializers.BooleanField(read_only=True)
    is_major_only = serializers.BooleanField(read_only=True)

    class Meta:
        model = SocialEvent
        fields = [
            "type",
            "id",
            "title",
            "status",
            "start_time",
            "end_time",
            "created_at",
            "creator",
            "is_faculty_only",
            "is_major_only",
        ]

    @extend_schema_field(serializers.CharField)
    def get_type(self, obj) -> str:
        return "event"


class SocialSharingRequestFeedSerializer(serializers.ModelSerializer):
    """Серіалізатор запиту на шеринг для відображення в загальній стрічці активностей."""

    creator = UserMapSerializer(read_only=True, help_text="Автор запиту")
    status = serializers.CharField(source="status.status", read_only=True, help_text="Поточний статус запиту")
    type = serializers.SerializerMethodField(help_text="Тип елемента стрічки")

    class Meta:
        model = SocialSharingRequest
        fields = ["type", "id", "title", "creator", "status", "created_at"]

    @extend_schema_field(serializers.CharField)
    def get_type(self, obj) -> str:
        return "sharing_request"


class SocialEventUpdateSerializer(serializers.ModelSerializer):
    """Серіалізатор для оновлення параметрів соціальної події."""

    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all(), required=False, allow_null=True)
    floor = serializers.PrimaryKeyRelatedField(queryset=Floor.objects.all(), required=False, allow_null=True)
    custom_location = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=255)

    class Meta:
        model = SocialEvent
        fields = [
            "title",
            "description",
            "start_time",
            "end_time",
            "max_person",
            "is_faculty_only",
            "is_major_only",
            "room",
            "floor",
            "custom_location",
        ]

    def validate(self, attrs):
        """Перевіряє валідність нових значень полів події при її зміні."""
        now = timezone.now()

        start_time = attrs.get("start_time", self.instance.start_time if self.instance else None)
        end_time = attrs.get("end_time", self.instance.end_time if self.instance else None)
        room = attrs.get("room", self.instance.room if self.instance else None)
        floor = attrs.get("floor", self.instance.floor if self.instance else None)

        if "custom_location" in attrs:
            custom_location = attrs["custom_location"]
            if custom_location is not None:
                custom_location = custom_location.strip() or None
                attrs["custom_location"] = custom_location
        else:
            custom_location = self.instance.custom_location if self.instance else None

        if "start_time" in attrs and attrs["start_time"] < now:
            raise serializers.ValidationError({"start_time": "Час початку події не може бути в минулому."})

        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError({"end_time": "Час завершення має бути пізніше часу початку."})

        if not room and not floor and not custom_location:
            raise serializers.ValidationError(
                {"detail": "Вкажіть хоча б одну локацію: кімнату, поверх або текстову назву місця."}
            )

        return attrs


class SocialSharingRequestUpdateSerializer(serializers.ModelSerializer):
    """Серіалізатор для редагування запиту на шеринг."""

    class Meta:
        model = SocialSharingRequest
        fields = ["title"]
        extra_kwargs = {
            "title": {"help_text": "Новий короткий опис речі або допомоги"},
        }
