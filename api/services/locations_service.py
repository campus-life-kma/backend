from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from api.models import Floor, Room, TargetType, User
from api.models.locations import Dormitory
from api.services.announcements_service import AnnouncementError, AnnouncementsService
from api.services.bookings_service import BookingError, BookingsService


class LocationsService:
    def get_floors_by_dormitory_id(self, dormitory_id) -> QuerySet[Floor]:
        try:
            dormitory = Dormitory.objects.get(id=dormitory_id)

            floors = Floor.objects.filter(dormitory=dormitory)

            return floors.order_by("number")

        except Dormitory.DoesNotExist:
            raise ValueError("Гуртожитку з таким id не знайдено!")

    def block_room(self, user, room_id) -> Room:
        room = self._get_room(room_id)
        now = timezone.now()
        bookings_service = BookingsService()

        with transaction.atomic():
            room.is_blocked = True
            room.save(update_fields=["is_blocked"])

            # Block every resource of the room and cancel its active bookings;
            # the cancellation announces the change to the affected users.
            for resource in room.resources.filter(is_blocked=False):
                resource.is_blocked = True
                resource.save(update_fields=["is_blocked"])
                try:
                    bookings_service.cancel_active_resource_bookings(resource, actor=user)
                except BookingError as exc:
                    raise ValueError(str(exc)) from exc

            # Cancel events that have not finished yet and notify everyone involved.
            events = room.events.filter(end_time__gte=now).select_related("creator").prefetch_related("participants")
            for event in events:
                recipients = {participant.id: participant for participant in event.participants.all()}
                recipients[event.creator.id] = event.creator
                recipients.pop(user.id, None)

                if recipients:
                    title = f"Скасування події: {event.title}"
                    message = (
                        f"Адміністратор {user.full_name} заблокував кімнату '{room.name}', "
                        f"тому подію '{event.title}' скасовано.\n\n"
                        f"За питаннями звертайтеся за адресою: {user.email}"
                    )
                    self._send_system_announcement(user, list(recipients.values()), title, message)

                event.delete()

            # Warn the residents of the blocked room.
            residents = list(User.objects.filter(room=room).exclude(id=user.id))
            if residents:
                title = f"Кімнату '{room.name}' заблоковано"
                message = (
                    f"Адміністратор {user.full_name} заблокував кімнату '{room.name}'. "
                    f"Бронювання ресурсів та івенти в ній скасовано.\n\n"
                    f"За питаннями звертайтеся за адресою: {user.email}"
                )
                self._send_system_announcement(user, residents, title, message)

        return room

    def unblock_room(self, user, room_id) -> Room:
        room = self._get_room(room_id)

        with transaction.atomic():
            room.is_blocked = False
            room.save(update_fields=["is_blocked"])

            room.resources.filter(is_blocked=True).update(is_blocked=False)

        return room

    def _get_room(self, room_id) -> Room:
        try:
            return Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            raise ValueError("Кімнату з таким id не знайдено!")

    def _send_system_announcement(self, actor, target_users, title, message):
        try:
            target_type = TargetType.objects.get(type="SPECIFIC_USERS")
        except TargetType.DoesNotExist:
            return

        announcement_data = {
            "target_type": target_type,
            "title": title,
            "message": message,
            "target_users": target_users,
        }

        try:
            AnnouncementsService().create_announcement(actor, announcement_data)
        except AnnouncementError as exc:
            raise ValueError("Не вдалося надіслати сповіщення користувачам. Дію скасовано.") from exc
