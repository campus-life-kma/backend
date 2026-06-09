from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from api.models import Presence, Room


class PresenceService:
    def check_in(self, user, room_id) -> Presence:
        try:
            room = Room.objects.select_related("room_type").get(id=room_id)
        except Room.DoesNotExist as exc:
            raise ValueError("Кімнату з таким id не знайдено.") from exc

        if room.is_blocked:
            raise ValueError("Ця кімната заблокована, тому в ній не можна відмітити присутність.")

        now = timezone.now()

        with transaction.atomic():
            presence, _ = Presence.objects.update_or_create(
                user=user,
                defaults={
                    "room": room,
                    "joined_at": now,
                    "expires_at": now + timedelta(hours=2),
                },
            )

        return presence

    def go_home(self, user) -> int:
        deleted_count, _ = Presence.objects.filter(user=user).delete()
        return deleted_count

    def get_current(self, user):
        now = timezone.now()
        return Presence.objects.select_related("room", "room__floor").filter(user=user, expires_at__gt=now).first()
