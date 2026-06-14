from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from api.models import Announcement, AnnouncementRead, TargetType, User
from api.services.announcement_email_service import AnnouncementEmailService


class AnnouncementError(Exception):
    """Базовий клас для винятків, пов'язаних з оголошеннями."""

    default_detail = "Сталася помилка оголошення."

    def __init__(self, detail=None):
        super().__init__(detail or self.default_detail)


class AnnouncementNotFoundError(AnnouncementError):
    """Виняток, який виникає, коли оголошення не знайдено."""

    default_detail = "Оголошення не знайдено."


class AnnouncementPermissionDeniedError(AnnouncementError):
    """Виняток, який виникає при спробі виконати дію без відповідних прав."""

    default_detail = "У вас немає прав для цієї дії."


class AnnouncementValidationError(AnnouncementError):
    """Виняток для помилок валідації даних оголошення."""

    default_detail = "Оголошення неможливо обробити."


class AnnouncementEmailSendError(AnnouncementError):
    """Виняток, який виникає у разі збою відправки email-сповіщень."""

    default_detail = "Не вдалося надіслати email-сповіщення отримувачам."


class AnnouncementsService:
    """Сервіс для роботи з оголошеннями, визначення отримувачів та маркування прочитаних."""

    recipient_ordering_fields = {
        "id": "id",
        "display_name": "full_name",
        "email": "email",
        "role": "role__name",
        "floor": "room__floor__number",
        "room": "room__name",
        "faculty": "major__faculty__name",
        "major": "major__name",
        "year": "year",
    }

    def get_active_announcements(self, user):
        """Повертає список активних оголошень, які призначені для користувача.

        Args:
            user: Об'єкт користувача, для якого підбираються оголошення.

        Returns:
            QuerySet: Активні та не прочитані оголошення.
        """
        now = timezone.now()
        user_floor_id = self.get_user_floor_id(user)

        target_filter = Q(target_type__type="GLOBAL") | Q(target_users=user)

        if user_floor_id:
            target_filter |= Q(target_type__type="FLOOR", target_floor_id=user_floor_id)

        if user.room_id:
            target_filter |= Q(target_type__type="ROOM", target_room_id=user.room_id)

        # Фільтруємо за часом дії та виключаємо безстрокові оголошення, які вже прочитані
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

    def get_available_recipients(self, user, filters):
        """Повертає список доступних адресатів для створення оголошень з урахуванням прав та фільтрів.

        Args:
            user: Користувач, який робить запит.
            filters: Словник з фільтрами та параметрами пошуку.

        Returns:
            QuerySet: Список користувачів-отримувачів.

        Raises:
            AnnouncementPermissionDeniedError: Якщо у користувача немає прав.
        """
        if not user.is_admin and not user.is_moderator:
            raise AnnouncementPermissionDeniedError("У вас немає прав для перегляду адресатів оголошень.")

        recipients = self.get_recipient_base_queryset(filters)
        recipients = self.scope_recipients_for_user(user, recipients, filters)
        recipients = self.apply_recipient_filters(recipients, filters)
        recipients = self.apply_recipient_search(recipients, filters.get("q"))
        ordering = filters.get("ordering") or "display_name"
        return recipients.order_by(*self.get_recipient_ordering(ordering))

    def get_recipient_base_queryset(self, filters=None):
        """Повертає базовий QuerySet для потенційних адресатів оголошення."""
        queryset = User.objects.exclude(email="").select_related(
            "role", "room", "room__floor", "room__floor__dormitory", "major", "major__faculty"
        )
        
        # За замовчуванням для оголошень повертаємо лише активованих
        if filters is None or "is_active" not in filters:
            queryset = queryset.filter(is_activated=True)
            
        return queryset

    def scope_recipients_for_user(self, user, recipients, filters):
        """Обмежує область видимості адресатів залежно від ролі користувача (модератор чи адмін).

        Args:
            user: Об'єкт користувача.
            recipients: Базовий QuerySet отримувачів.
            filters: Фільтри запиту.

        Returns:
            QuerySet: Обмежений QuerySet отримувачів.
        """
        if user.is_moderator:
            user_floor_id = self.get_user_floor_id(user)
            if not user_floor_id:
                raise AnnouncementPermissionDeniedError("Голова поверху має бути прив'язаний до свого поверху.")
            return recipients.filter(room__floor_id=user_floor_id)

        floor_id = filters.get("floor_id")
        if floor_id:
            return recipients.filter(room__floor_id=floor_id)

        return recipients

    def apply_recipient_filters(self, recipients, filters):
        """Застосовує точні фільтри (кімната, факультет, спеціальність, роль, курс)."""
        filter_map = {
            "room_id": "room_id",
            "faculty_id": "major__faculty_id",
            "major_id": "major_id",
            "role": "role__name",
            "year": "year",
            "position": "position",
        }

        for filter_key, query_key in filter_map.items():
            value = filters.get(filter_key)
            if value:
                recipients = recipients.filter(**{query_key: value})

        is_active = filters.get("is_active")
        if is_active is not None and str(is_active).lower() != "all":
            is_active_bool = str(is_active).lower() == "true"
            recipients = recipients.filter(is_activated=is_active_bool)

        return recipients

    def apply_recipient_search(self, recipients, query):
        """Виконує текстовий пошук по імені, пошті, кімнаті, факультету, спеціальності та ролі."""
        if not query:
            return recipients

        return recipients.filter(
            Q(full_name__icontains=query)
            | Q(email__icontains=query)
            | Q(room__name__icontains=query)
            | Q(role__name__icontains=query)
            | Q(major__name__icontains=query)
            | Q(major__faculty__name__icontains=query)
        )

    def get_recipient_ordering(self, ordering):
        """Формує параметри сортування результатів за вказаним полем.

        Args:
            ordering: Рядок із параметрами сортування.

        Returns:
            list: Список полів для сортування.
        """
        fields = []
        for raw_field in ordering.split(","):
            raw_field = raw_field.strip()
            if not raw_field:
                continue

            descending = raw_field.startswith("-")
            field_name = raw_field[1:] if descending else raw_field
            mapped_field = self.recipient_ordering_fields.get(field_name)
            if not mapped_field:
                allowed_fields = ", ".join(self.recipient_ordering_fields)
                raise AnnouncementValidationError(f"Некоректне сортування. Доступні поля: {allowed_fields}.")

            fields.append(f"-{mapped_field}" if descending else mapped_field)

        fields.append("email")
        return fields

    def mark_as_read(self, user, announcement_id) -> Announcement:
        """Позначає оголошення як прочитане користувачем.

        Args:
            user: Об'єкт користувача.
            announcement_id: Ідентифікатор оголошення.

        Returns:
            Announcement: Позначене оголошення.
        """
        try:
            announcement = Announcement.objects.select_related("target_type", "target_floor", "target_room").get(
                id=announcement_id
            )
        except Announcement.DoesNotExist as exc:
            raise AnnouncementNotFoundError("Оголошення з таким id не знайдено.") from exc

        if not self.can_user_see_announcement(user, announcement):
            raise AnnouncementPermissionDeniedError("Це оголошення не призначене для вас.")

        AnnouncementRead.objects.get_or_create(announcement=announcement, user=user)
        return announcement

    def create_announcement(self, user, validated_data) -> Announcement:
        """Створює нове оголошення та ініціює розсилку електронної пошти отримувачам.

        Args:
            user: Створювач оголошення.
            validated_data: Валідовані дані оголошення.

        Returns:
            Announcement: Створене оголошення.
        """
        target_type = validated_data["target_type"]

        self.validate_create_permissions(user, target_type, validated_data)

        target_users = validated_data.pop("target_users", [])

        expires_at = validated_data.get("expires_at")
        if expires_at and expires_at <= timezone.now():
            raise AnnouncementValidationError("Час завершення оголошення має бути в майбутньому.")

        # Використовуємо транзакцію для створення оголошення та автоматичної розсилки сповіщень
        with transaction.atomic():
            announcement = Announcement.objects.create(creator=user, **validated_data)
            if target_users:
                announcement.target_users.set(target_users)

            try:
                AnnouncementEmailService().send_announcement(announcement)
            except Exception as exc:
                raise AnnouncementEmailSendError("Не вдалося надіслати email-сповіщення отримувачам.") from exc

        return announcement

    def validate_create_permissions(self, user, target_type, validated_data):
        """Перевіряє права користувача на створення оголошення для обраної цільової аудиторії."""
        if user.is_admin:
            return

        if not user.is_moderator:
            raise AnnouncementPermissionDeniedError("У вас немає прав для створення оголошень.")

        # Модератор (голова поверху) може створювати оголошення лише на свій поверх
        if target_type.type == "FLOOR":
            target_floor = validated_data.get("target_floor")
            if not target_floor:
                raise AnnouncementValidationError("Для оголошення на поверх необхідно обрати поверх.")

            if self.get_user_floor_id(user) != target_floor.id:
                raise AnnouncementPermissionDeniedError(
                    "Голова поверху може створювати оголошення лише для свого поверху."
                )

        # Або конкретним мешканцям свого поверху
        elif target_type.type == "SPECIFIC_USERS":
            target_users = validated_data.get("target_users", [])
            mod_floor_id = self.get_user_floor_id(user)

            for t_user in target_users:
                if self.get_user_floor_id(t_user) != mod_floor_id:
                    raise AnnouncementPermissionDeniedError(
                        "Голова поверху може сповіщати лише мешканців свого поверху."
                    )
        else:
            raise AnnouncementPermissionDeniedError(
                "Голова поверху може створювати оголошення лише для свого поверху або конкретних мешканців."
            )

    def can_user_see_announcement(self, user, announcement) -> bool:
        """Перевіряє, чи має користувач доступ до перегляду вказаного оголошення."""
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
        """Допоміжний метод для отримання ідентифікатора поверху користувача."""
        if user.room_id:
            return user.room.floor_id

        return None

    def get_target_type(self, target_type) -> TargetType:
        """Отримує об'єкт TargetType за його назвою."""
        try:
            return TargetType.objects.get(type=target_type)
        except TargetType.DoesNotExist as exc:
            raise AnnouncementValidationError("Такого типу аудиторії не існує.") from exc
