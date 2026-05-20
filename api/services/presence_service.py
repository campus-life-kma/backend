from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from api.models import Presence, Room


class PresenceRoomNotFoundError(Exception):
    pass


class PresenceRoomBlockedError(Exception):
    pass


class PresenceLivingRoomError(Exception):
    pass


class PresenceService:
    def check_in(self, user, room_id) -> Presence:
        try:
            room = Room.objects.select_related("room_type").get(id=room_id)
        except Room.DoesNotExist as exc:
            raise PresenceRoomNotFoundError("Room with this id was not found.") from exc

        if room.is_blocked:
            raise PresenceRoomBlockedError("This room is blocked and cannot be used for presence.")

        if room.room_type.type == "LIVING":
            raise PresenceLivingRoomError("Check-in is available only for shared spaces.")

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
