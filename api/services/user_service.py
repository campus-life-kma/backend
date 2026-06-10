from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from api.models import Room, User
from api.serializers.user_serializer import (
    AdminUserUpdateSerializer,
    ModeratorUserUpdateSerializer,
    UserUpdateSerializer,
)


class UserService:
    def get_user_by_id(self, user_id: str) -> User:
        try:
            return User.objects.select_related("role", "room__floor", "room__room_type", "major__faculty").get(
                id=user_id
            )
        except User.DoesNotExist:
            raise NotFound(detail="Користувача з таким id не знайдено!")

    def update_profile(self, acting_user: User, target_user_id: str, update_data: dict) -> User:
        target_user = self.get_user_by_id(target_user_id)

        can_moderator_edit = self.can_moderator_edit_profile(acting_user, target_user)

        if not acting_user.is_admin and acting_user.id != target_user.id and not can_moderator_edit:
            raise PermissionDenied(detail="Ви не маєте прав для редагування цього профілю.")

        if acting_user.is_admin:
            serializer_class = AdminUserUpdateSerializer
        elif can_moderator_edit:
            self.validate_moderator_profile_update(update_data)
            serializer_class = ModeratorUserUpdateSerializer
        else:
            serializer_class = UserUpdateSerializer

        serializer = serializer_class(target_user, data=update_data, partial=True)

        if not serializer.is_valid():
            raise ValidationError(serializer.errors)

        with transaction.atomic():
            if acting_user.is_admin:
                self.validate_admin_room_change(target_user, serializer.validated_data)
                changes = self.build_profile_changes(target_user, serializer.validated_data)
                updated_user = serializer.save()
                self.notify_profile_updated(updated_user, changes, "Адміністратор")
                return updated_user

            if can_moderator_edit:
                changes = self.build_profile_changes(target_user, serializer.validated_data)
                updated_user = serializer.save()
                self.notify_profile_updated(updated_user, changes, "Модератор поверху")
                return updated_user

            return serializer.save()

    def can_moderator_edit_profile(self, acting_user: User, target_user: User) -> bool:
        return bool(
            acting_user.is_moderator
            and acting_user.id != target_user.id
            and acting_user.room_id
            and target_user.room_id
            and acting_user.room.floor_id == target_user.room.floor_id
        )

    def validate_moderator_profile_update(self, update_data: dict):
        allowed_fields = {"status", "bio"}
        forbidden_fields = set(update_data.keys()) - allowed_fields
        if forbidden_fields:
            raise PermissionDenied(detail="Модератор може редагувати лише статус і біо мешканців свого поверху.")

    def validate_admin_room_change(self, target_user: User, validated_data: dict):
        if "room" not in validated_data:
            return

        room = validated_data["room"]
        if room is None:
            return

        room = Room.objects.select_related("floor", "room_type").select_for_update().get(id=room.id)

        if room.room_type.type != "LIVING":
            raise ValidationError({"room": ["Користувача можна поселити лише в житлову кімнату."]})

        if room.is_blocked:
            raise ValidationError({"room": ["Ця кімната заблокована, тому поселення в неї недоступне."]})

        resident_ids = list(
            User.objects.select_for_update().filter(room=room).exclude(id=target_user.id).values_list("id", flat=True)
        )
        if len(resident_ids) >= room.max_person:
            raise ValidationError({"room": ["У цій кімнаті немає вільних місць."]})

    def build_profile_changes(self, target_user: User, validated_data: dict):
        changes = []
        labels = {
            "role": "Роль",
            "full_name": "Ім'я",
            "email": "Пошта",
            "photo": "Аватар",
            "room": "Кімната проживання",
            "major": "Спеціальність",
            "education_level": "Рівень навчання",
            "year": "Курс",
            "status": "Статус",
            "bio": "Біо",
        }

        for field, new_value in validated_data.items():
            old_value = getattr(target_user, field)
            if not self.profile_values_equal(field, old_value, new_value):
                changes.append(
                    {
                        "field": labels.get(field, field),
                        "old": self.format_profile_value(field, old_value),
                        "new": self.format_profile_value(field, new_value),
                    }
                )

        return changes

    def profile_values_equal(self, field: str, old_value, new_value) -> bool:
        if field in {"role", "room", "major"}:
            old_id = getattr(old_value, "id", None)
            new_id = getattr(new_value, "id", None)
            return old_id == new_id

        if field == "photo":
            return not new_value

        return old_value == new_value

    def format_profile_value(self, field: str, value) -> str:
        if value in (None, ""):
            return "не вказано"

        if field == "role":
            return value.name

        if field == "room":
            return f"{value.name}, {value.floor.number} поверх"

        if field == "major":
            return f"{value.name} ({value.faculty.name})"

        if field == "education_level":
            return self.format_education_level(value)

        if field == "photo":
            return "оновлено"

        return str(value)

    def format_education_level(self, value: str) -> str:
        labels = {
            User.EducationLevel.BACHELOR: "Бакалавр",
            User.EducationLevel.MASTER: "Магістр",
            User.EducationLevel.PHD: "Аспірант",
        }
        return labels.get(value, value)

    def notify_profile_updated(self, user: User, changes: list[dict], actor_label: str):
        if not changes or not user.is_activated or not user.email:
            return

        changes_text = "\n".join(
            f"- {change['field']}: було «{change['old']}», стало «{change['new']}»" for change in changes
        )
        body = (
            "Вітаємо!\n\n"
            f"{actor_label} Campus Life оновив дані вашого профілю:\n\n"
            f"{changes_text}\n\n"
            "Якщо ви вважаєте, що сталася помилка, зверніться до адміністрації гуртожитку."
        )

        send_mail(
            subject="Campus Life: ваш профіль оновлено",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
