from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from api.models import Floor, Room, Resource, SocialSharingStatus, TargetType, User
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
        if room.user_set.exists():
            raise ValueError("Не можна заблокувати кімнату, в якій є мешканці.")

        now = timezone.now()
        bookings_service = BookingsService()

        with transaction.atomic():
            room.is_blocked = True
            room.save(update_fields=["is_blocked"])

            for resource in room.resources.filter(is_blocked=False):
                resource.is_blocked = True
                resource.save(update_fields=["is_blocked"])
                try:
                    bookings_service.cancel_active_resource_bookings(resource, actor=user)
                except BookingError as exc:
                    raise ValueError(str(exc)) from exc

            cancelled_event_status, _ = SocialSharingStatus.objects.get_or_create(status="CANCELLED")
            events = (
                room.events.filter(status__status="ACTIVE", end_time__gte=now)
                .select_related("creator")
                .prefetch_related("participants")
            )
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

                event.status = cancelled_event_status
                event.save(update_fields=["status"])

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

    def update_room(self, user, room_id, data) -> Room:  # noqa: C901
        room = self._get_room(room_id)

        is_blocked_new = data.pop("is_blocked", None)

        if is_blocked_new is True and room.user_set.exists():
            raise ValueError("Не можна заблокувати кімнату, в якій є мешканці.")

        room_type_new = data.get("room_type")
        if room_type_new:
            if room_type_new.type not in ["KITCHEN", "LAUNDRY"]:
                if room.resources.exists():
                    raise ValueError("Не можна змінити тип кімнати, якщо в ній є додані ресурси. Спочатку видаліть їх.")
            else:
                if room.resources.exists():
                    kitchen_resources = ["OVEN", "COOKTOP", "STOVE", "MICROWAVE", "FRIDGE"]
                    laundry_resources = ["WASHING_MACHINE", "DRYER", "IRON"]
                    existing_resource_types = [res.resource_type.type for res in room.resources.all()]

                    if room_type_new.type == "KITCHEN":
                        invalid = [rt for rt in existing_resource_types if rt not in kitchen_resources]
                        if invalid:
                            raise ValueError(
                                "У кімнаті є інвентар (наприклад, пральна машина), що не підходить для кухні."
                            )
                    elif room_type_new.type == "LAUNDRY":
                        invalid = [rt for rt in existing_resource_types if rt not in laundry_resources]
                        if invalid:
                            raise ValueError("У кімнаті є інвентар (наприклад, плита), що не підходить для пральні.")
            if room_type_new.type in ["KITCHEN", "LAUNDRY", "TOILET", "BATHROOM"]:
                if room.user_set.exists():
                    raise ValueError(
                        "Не можна зробити кімнату нежитловою, оскільки "
                        "в ній зараз проживають студенти. Спочатку переселіть їх."
                    )

        new_name = data.get("name")
        if new_name and new_name != room.name:
            if Room.objects.filter(floor__dormitory=room.floor.dormitory, name=new_name).exclude(id=room.id).exists():
                raise ValueError("Кімната з такою назвою вже існує в цьому гуртожитку.")

        with transaction.atomic():
            for key, value in data.items():
                setattr(room, key, value)
            room.save()

        # Якщо статус блокування змінився
        if is_blocked_new is not None and is_blocked_new != room.is_blocked:
            if is_blocked_new:
                self.block_room(user, room_id)
            else:
                self.unblock_room(user, room_id)

        room.refresh_from_db()
        return room

    def create_resource(self, user, room_id, data) -> Resource:
        room = self._get_room(room_id)
        if room.room_type.type not in ["KITCHEN", "LAUNDRY"]:
            raise ValueError("Ресурси можна додавати лише в кухні та пральні.")

        resource_type = data.get("resource_type")
        if resource_type:
            kitchen_resources = ["OVEN", "COOKTOP", "STOVE", "MICROWAVE", "FRIDGE"]
            laundry_resources = ["WASHING_MACHINE", "DRYER", "IRON"]

            if room.room_type.type == "KITCHEN" and resource_type.type in laundry_resources:
                raise ValueError("Цей тип ресурсу не підходить для кухні.")
            if room.room_type.type == "LAUNDRY" and resource_type.type in kitchen_resources:
                raise ValueError("Цей тип ресурсу не підходить для пральні.")

        data["room"] = room
        return Resource.objects.create(**data)

    def update_resource(self, user, resource_id, data) -> Resource:
        try:
            resource = Resource.objects.get(id=resource_id)
        except Resource.DoesNotExist:
            raise ValueError("Ресурс не знайдено!")

        for key, value in data.items():
            setattr(resource, key, value)
        resource.save()
        return resource

    def delete_resource(self, user, resource_id):
        try:
            resource = Resource.objects.get(id=resource_id)
            resource.delete()
        except Resource.DoesNotExist:
            raise ValueError("Ресурс не знайдено!")

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
