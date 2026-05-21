from django.db.models import Q
from django.utils import timezone

from api.models import Announcement, AnnouncementRead, TargetType
from api.services.announcement_email_service import AnnouncementEmailService


class AnnouncementsService:
    def get_active_announcements(self, user):
        now = timezone.now()
        user_floor_id = self.get_user_floor_id(user)

        target_filter = Q(target_type__type="GLOBAL") | Q(target_users=user)

        if user_floor_id:
            target_filter |= Q(target_type__type="FLOOR", target_floor_id=user_floor_id)

        if user.room_id:
            target_filter |= Q(target_type__type="ROOM", target_room_id=user.room_id)

        announcements = (
            Announcement.objects.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
            .filter(target_filter)
            .exclude(expires_at__isnull=True, reads__user=user)
            .select_related("creator", "target_type", "target_floor", "target_room")
            .prefetch_related("target_users")
            .distinct()
            .order_by("-is_pinned", "-created_at")
        )

        return announcements

    def mark_as_read(self, user, announcement_id):
        try:
            announcement = Announcement.objects.select_related("target_type", "target_floor", "target_room").get(
                id=announcement_id
            )
        except Announcement.DoesNotExist as exc:
            raise ValueError("Оголошення з таким id не знайдено.") from exc

        if not self.can_user_see_announcement(user, announcement):
            raise ValueError("Це оголошення не призначене для вас.")

        AnnouncementRead.objects.get_or_create(announcement=announcement, user=user)
        return announcement

    def create_announcement(self, user, validated_data):
        target_users = validated_data.pop("target_users", [])
        target_type = validated_data["target_type"]

        self.validate_create_permissions(user, target_type, validated_data)

        expires_at = validated_data.get("expires_at")
        if expires_at and expires_at <= timezone.now():
            raise ValueError("Час завершення оголошення має бути в майбутньому.")

        announcement = Announcement.objects.create(creator=user, **validated_data)
        if target_users:
            announcement.target_users.set(target_users)

        try:
            AnnouncementEmailService().send_announcement(announcement)
        except Exception as exc:
            raise ValueError("Не вдалося надіслати email-сповіщення отримувачам.") from exc

        return announcement

    def validate_create_permissions(self, user, target_type, validated_data):
        if user.is_admin:
            return

        if not user.is_moderator:
            raise ValueError("У вас немає прав для створення оголошень.")

        if target_type.type != "FLOOR":
            raise ValueError("Голова поверху може створювати оголошення лише для свого поверху.")

        target_floor = validated_data.get("target_floor")
        if not target_floor:
            raise ValueError("Для оголошення на поверх необхідно обрати поверх.")

        if self.get_user_floor_id(user) != target_floor.id:
            raise ValueError("Голова поверху може створювати оголошення лише для свого поверху.")

    def can_user_see_announcement(self, user, announcement):
        target_type = announcement.target_type.type

        if announcement.expires_at and announcement.expires_at <= timezone.now():
            return False

        if target_type == "GLOBAL":
            return True

        if target_type == "FLOOR":
            return self.get_user_floor_id(user) == announcement.target_floor_id

        if target_type == "ROOM":
            return user.room_id == announcement.target_room_id

        if target_type == "SPECIFIC_USERS":
            return announcement.target_users.filter(id=user.id).exists()

        return False

    def get_user_floor_id(self, user):
        if user.room_id:
            return user.room.floor_id

        return None

    def get_target_type(self, target_type):
        try:
            return TargetType.objects.get(type=target_type)
        except TargetType.DoesNotExist as exc:
            raise ValueError("Такого типу аудиторії не існує.") from exc
