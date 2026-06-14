import xml.etree.ElementTree as ET

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from api.models import Floor, Room, Resource, SocialSharingStatus, TargetType, User
from api.models.locations import Dormitory
from api.services.announcements_service import AnnouncementError, AnnouncementsService
from api.services.bookings_service import BookingError, BookingsService


class LocationsService:
    """Сервіс для роботи з локаціями (кімнати, поверхи) та управлінням ресурсами."""

    def get_floors_by_dormitory_id(self, dormitory_id) -> QuerySet[Floor]:
        """Отримує список усіх поверхів певного гуртожитку.

        Args:
            dormitory_id: Ідентифікатор гуртожитку.

        Returns:
            QuerySet[Floor]: Список поверхів, відсортований за номером.

        Raises:
            ValueError: Якщо гуртожитку з таким ID не знайдено.
        """
        try:
            dormitory = Dormitory.objects.get(id=dormitory_id)
            floors = Floor.objects.filter(dormitory=dormitory)
            return floors.order_by("number")
        except Dormitory.DoesNotExist:
            raise ValueError("Гуртожитку з таким id не знайдено!")

    def block_room(self, user, room_id) -> Room:
        """Блокує кімнату, скасовуючи всі активні події та бронювання її ресурсів.

        Args:
            user: Користувач-адміністратор, який ініціював блокування.
            room_id: Ідентифікатор кімнати.

        Returns:
            Room: Заблокована кімната.

        Raises:
            ValueError: У разі помилок скасування чи якщо кімнату не знайдено.
        """
        room = self._get_room(room_id)
        now = timezone.now()
        bookings_service = BookingsService()

        with transaction.atomic():
            room.is_blocked = True
            room.save(update_fields=["is_blocked"])

            # Блокуємо всі ресурси кімнати та скасовуємо їх бронювання
            for resource in room.resources.filter(is_blocked=False):
                resource.is_blocked = True
                resource.save(update_fields=["is_blocked"])
                try:
                    bookings_service.cancel_active_resource_bookings(resource, actor=user)
                except BookingError as exc:
                    raise ValueError(str(exc)) from exc

            # Скасовуємо всі активні майбутні події у цій кімнаті
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

                # Сповіщаємо учасників події про скасування
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

            # Сповіщаємо мешканців кімнати про блокування
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
        """Розблоковує кімнату та всі її ресурси.

        Args:
            user: Користувач-адміністратор.
            room_id: Ідентифікатор кімнати.

        Returns:
            Room: Розблокована кімната.
        """
        room = self._get_room(room_id)

        with transaction.atomic():
            room.is_blocked = False
            room.save(update_fields=["is_blocked"])
            room.resources.filter(is_blocked=True).update(is_blocked=False)

        return room

    def update_room(self, user, room_id, data) -> Room:  # noqa: C901
        """Оновлює параметри кімнати з перевіркою валідності зміни типу та назви.

        Args:
            user: Користувач-адміністратор.
            room_id: Ідентифікатор кімнати.
            data: Нові дані для оновлення.

        Returns:
            Room: Оновлена кімната.

        Raises:
            ValueError: Якщо нові параметри суперечать логіці системи.
        """
        room = self._get_room(room_id)
        is_blocked_new = data.pop("is_blocked", None)

        room_type_new = data.get("room_type")
        if room_type_new:
            # Якщо змінюємо тип кімнати з пральні чи кухні на інший
            if room_type_new.type not in ["KITCHEN", "LAUNDRY"]:
                if room.resources.exists():
                    raise ValueError("Не можна змінити тип кімнати, якщо в ній є додані ресурси. Спочатку видаліть їх.")
            else:
                # Перевіряємо сумісність ресурсів з новим типом кімнати
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
            # Перевіряємо, чи в кімнаті проживають люди при спробі зробити її нежитловою
            if room_type_new.type != "LIVING":
                if room.user_set.exists():
                    raise ValueError(
                        "Не можна зробити кімнату нежитловою, оскільки в ній зараз проживають студенти. "
                        "Спочатку переселіть їх."
                    )

        new_name = data.get("name")
        if new_name and new_name != room.name:
            if Room.objects.filter(floor__dormitory=room.floor.dormitory, name=new_name).exclude(id=room.id).exists():
                raise ValueError("Кімната з такою назвою вже існує в цьому гуртожитку.")

        max_person_new = data.get("max_person")
        if max_person_new is not None:
            current_residents_count = room.user_set.count()
            if max_person_new < current_residents_count:
                raise ValueError(
                    f"Не можна встановити місткість ({max_person_new}), яка менша за "
                    f"поточну кількість мешканців ({current_residents_count})."
                )

        with transaction.atomic():
            for key, value in data.items():
                setattr(room, key, value)
            room.save()

        # Якщо передано статус блокування, викликаємо відповідні процедури
        if is_blocked_new is not None and is_blocked_new != room.is_blocked:
            if is_blocked_new:
                self.block_room(user, room_id)
            else:
                self.unblock_room(user, room_id)

        room.refresh_from_db()
        return room

    def delete_room(self, user, room_id):
        """Видаляє кімнату з бази даних, якщо вона заблокована та не містить зв'язаних даних.

        Args:
            user: Користувач-адміністратор.
            room_id: Ідентифікатор кімнати.

        Raises:
            ValueError: Якщо видалення неможливе (є активні бронювання, мешканці тощо).
        """
        room = self._get_room(room_id)

        if not room.is_blocked:
            raise ValueError("Спочатку заблокуйте кімнату, а потім вилучайте її з гуртожитку.")
        if room.user_set.exists():
            raise ValueError("Не можна вилучити кімнату, доки до неї прикріплені мешканці.")
        if room.presences.filter(expires_at__gt=timezone.now()).exists():
            raise ValueError("Не можна вилучити кімнату, доки в ній є активна присутність користувачів.")
        if room.resources.filter(bookings__status__status="ACTIVE").exists():
            raise ValueError("Не можна вилучити кімнату, доки її ресурси мають активні бронювання.")
        if room.events.filter(status__status="ACTIVE").exists():
            raise ValueError("Не можна вилучити кімнату, доки в ній є активні події.")

        room.delete()

    def create_room(self, user, floor_id, data) -> Room:
        """Створює нову кімнату на поверсі, перевіряючи наявність відповідної карти SVG.

        Args:
            user: Користувач-адміністратор.
            floor_id: Ідентифікатор поверху.
            data: Параметри кімнати.

        Returns:
            Room: Створена кімната.

        Raises:
            ValueError: Якщо ID у SVG-файлі відсутній або кімната з таким ім'ям вже є.
        """
        try:
            floor = Floor.objects.select_related("dormitory").get(id=floor_id)
        except Floor.DoesNotExist:
            raise ValueError("Поверх з таким id не знайдено!")

        svg_element_id = data.get("svg_element_id")
        if Room.objects.filter(floor=floor, svg_element_id=svg_element_id).exists():
            raise ValueError("Ця зона мапи вже прив'язана до кімнати.")

        if not self._floor_has_svg_room_id(floor, svg_element_id):
            raise ValueError("У SVG-мапі цього поверху немає такої кімнати.")

        name = data.get("name")
        if Room.objects.filter(floor__dormitory=floor.dormitory, name=name).exists():
            raise ValueError("Кімната з такою назвою вже існує в цьому гуртожитку.")

        data["floor"] = floor
        return Room.objects.create(**data)

    def create_resource(self, user, room_id, data) -> Resource:
        """Створює новий ресурс у кімнаті (тільки для кухні або пральні).

        Args:
            user: Користувач-адміністратор.
            room_id: Ідентифікатор кімнати.
            data: Дані ресурсу.

        Returns:
            Resource: Створений ресурс.
        """
        room = self._get_room(room_id)
        if room.room_type.type not in ["KITCHEN", "LAUNDRY"]:
            raise ValueError("Ресурси можна додавати лише в кухні та пральні.")

        resource_type = data.get("resource_type")
        if resource_type:
            self._validate_resource_type_for_room(room, resource_type)

        data["room"] = room
        return Resource.objects.create(**data)

    def update_resource(self, user, resource_id, data) -> Resource:
        """Оновлює параметри ресурсу.

        Args:
            user: Користувач-адміністратор.
            resource_id: Ідентифікатор ресурсу.
            data: Дані оновлення.

        Returns:
            Resource: Оновлений ресурс.
        """
        try:
            resource = Resource.objects.select_related("room", "room__room_type", "resource_type").get(id=resource_id)
        except Resource.DoesNotExist:
            raise ValueError("Ресурс не знайдено!")

        resource_type = data.get("resource_type")
        if resource_type:
            self._validate_resource_type_for_room(resource.room, resource_type)

        for key, value in data.items():
            setattr(resource, key, value)
        resource.save()
        return resource

    def delete_resource(self, user, resource_id):
        """Видаляє ресурс за його ID.

        Args:
            user: Користувач-адміністратор.
            resource_id: Ідентифікатор ресурсу.
        """
        try:
            resource = Resource.objects.get(id=resource_id)
            resource.delete()
        except Resource.DoesNotExist:
            raise ValueError("Ресурс не знайдено!")

    def _get_room(self, room_id) -> Room:
        """Допоміжний метод для отримання об'єкта кімнати."""
        try:
            return Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            raise ValueError("Кімнату з таким id не знайдено!")

    def _floor_has_svg_room_id(self, floor: Floor, svg_element_id: str) -> bool:
        """Перевіряє, чи містить завантажена карта поверху SVG елемент із вказаним id.

        Args:
            floor: Об'єкт поверху.
            svg_element_id: Ідентифікатор SVG-елемента.

        Returns:
            bool: True, якщо елемент присутній в групі 'rooms'.
        """
        if not floor.map_file:
            raise ValueError("Для цього поверху не завантажено SVG-мапу.")

        try:
            with floor.map_file.open("rb") as file:
                root = ET.parse(file).getroot()
        except (OSError, ET.ParseError, ValueError) as exc:
            raise ValueError("Не вдалося перевірити SVG-мапу поверху.") from exc

        rooms_group = None
        for element in root.iter():
            if element.attrib.get("id") == "rooms":
                rooms_group = element
                break

        if rooms_group is None:
            raise ValueError("У SVG-мапі не знайдено групу кімнат.")

        for element in rooms_group.iter():
            if element.attrib.get("id") == svg_element_id:
                return True
        return False

    def _send_system_announcement(self, actor, target_users, title, message):
        """Створює внутрішнє оголошення через AnnouncementsService."""
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

    def _validate_resource_type_for_room(self, room: Room, resource_type):
        """Перевіряє сумісність типу ресурсу з типом кімнати (кухня/пральня)."""
        kitchen_resources = ["OVEN", "COOKTOP", "STOVE", "MICROWAVE", "FRIDGE"]
        laundry_resources = ["WASHING_MACHINE", "DRYER", "IRON"]

        if room.room_type.type == "KITCHEN" and resource_type.type in laundry_resources:
            raise ValueError("Цей тип ресурсу не підходить для кухні.")
        if room.room_type.type == "LAUNDRY" and resource_type.type in kitchen_resources:
            raise ValueError("Цей тип ресурсу не підходить для пральні.")
