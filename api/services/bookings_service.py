from datetime import datetime, time, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date

from api.models import Booking, BookingStatus, Resource, TargetType
from api.services.announcements_service import AnnouncementsService, AnnouncementError


class BookingError(Exception):
    """Базовий клас для винятків, пов'язаних із бронюванням ресурсів."""

    default_detail = "Сталася помилка бронювання."

    def __init__(self, detail=None):
        super().__init__(detail or self.default_detail)


class BookingNotFoundError(BookingError):
    """Виняток, який виникає, коли об'єкт бронювання або ресурс не знайдено."""

    default_detail = "Об'єкт не знайдено."


class BookingPermissionDeniedError(BookingError):
    """Виняток, який виникає при спробі виконати дію з бронюванням без відповідних прав."""

    default_detail = "У вас немає прав для цієї дії."


class BookingValidationError(BookingError):
    """Виняток для помилок валідації часу, заповненості чи доступності ресурсу."""

    default_detail = "Бронювання неможливо виконати."


class BookingStatusNotFoundError(BookingError):
    """Виняток, який виникає, коли необхідний статус бронювання відсутній у БД."""

    default_detail = "Потрібний статус бронювання не знайдено в базі даних."


class BookingsService:
    """Сервіс для керування бронюваннями ресурсів, їх скасуванням та блокуванням."""

    def get_resource_schedule(self, resource_id, start_date_str=None, end_date_str=None):
        """Отримує розклад бронювань для ресурсу у вказаному діапазоні дат.

        Args:
            resource_id: Ідентифікатор ресурсу.
            start_date_str: Початкова дата діапазону в форматі YYYY-MM-DD.
            end_date_str: Кінцева дата діапазону в форматі YYYY-MM-DD.

        Returns:
            QuerySet: Список активних бронювань для ресурсу у вказаний проміжок часу.
        """
        resource = self.get_resource(resource_id)
        active_status = self.get_status("ACTIVE")
        start_range, end_range = self._parse_date_range(start_date_str, end_date_str)

        return (
            Booking.objects.filter(
                resource=resource,
                status=active_status,
                start_time__lt=end_range,
                end_time__gt=start_range,
            )
            .select_related("status", "user")
            .order_by("start_time")
        )

    def _parse_date_range(self, start_date_str, end_date_str):
        """Парсить часовий діапазон для розкладу з урахуванням локальної часової зони.

        Args:
            start_date_str: Рядок початкової дати.
            end_date_str: Рядок кінцевої дати.

        Returns:
            tuple: Початок та кінець діапазону як aware datetime.
        """
        current_timezone = timezone.get_current_timezone()

        if start_date_str:
            start_date = parse_date(start_date_str)
            if not start_date:
                raise BookingValidationError("Некоректний формат start_date. Використовуйте YYYY-MM-DD.")
        else:
            start_date = timezone.localdate()

        if end_date_str:
            end_date = parse_date(end_date_str)
            if not end_date:
                raise BookingValidationError("Некоректний формат end_date. Використовуйте YYYY-MM-DD.")
        else:
            end_date = start_date + timedelta(days=1)

        if start_date > end_date:
            raise BookingValidationError("Початкова дата не може бути більшою за кінцеву.")

        # Створюємо aware дати початку (00:00) та кінця (23:59:59)
        start_range = timezone.make_aware(datetime.combine(start_date, time.min), current_timezone)
        end_range = timezone.make_aware(datetime.combine(end_date, time.max), current_timezone)

        return start_range, end_range

    def create_booking(self, user, validated_data) -> Booking:
        """Створює нове бронювання ресурсу з перевіркою конфліктів та місткості.

        Args:
            user: Користувач, який здійснює бронювання.
            validated_data: Перевірені дані бронювання (ресурс, час початку, час завершення).

        Returns:
            Booking: Об'єкт створеного бронювання.
        """
        resource_id = validated_data["resource"].id
        start_time = validated_data["start_time"]
        end_time = validated_data["end_time"]

        # Блокуємо рядок ресурсу для уникнення race conditions при конкурентних запитах
        with transaction.atomic():
            try:
                resource = (
                    Resource.objects.select_for_update().select_related("room", "room__floor").get(id=resource_id)
                )
            except Resource.DoesNotExist as exc:
                raise BookingNotFoundError("Ресурс з таким id не знайдено.") from exc

            if resource.is_blocked:
                raise BookingValidationError("Цей ресурс заблокований і недоступний для бронювання.")

            active_status = self.get_status("ACTIVE")
            overlapping_booking_ids = list(
                Booking.objects.filter(
                    resource=resource,
                    status=active_status,
                    start_time__lt=end_time,
                    end_time__gt=start_time,
                )
                .select_for_update()
                .values_list("id", flat=True)
            )

            # Перевіряємо, чи кількість паралельних бронювань не перевищує ліміт ресурсу
            if len(overlapping_booking_ids) >= resource.max_person:
                raise BookingValidationError("На цей час ресурс уже повністю зайнятий.")

            booking = Booking.objects.create(
                user=user,
                resource=resource,
                start_time=start_time,
                end_time=end_time,
                status=active_status,
            )

        return booking

    def get_my_bookings(self, user):
        """Повертає список майбутніх та активних бронювань користувача.

        Args:
            user: Об'єкт користувача.

        Returns:
            QuerySet: Список бронювань користувача.
        """
        active_status = self.get_status("ACTIVE")
        cancelled_status = self.get_status("CANCELLED")
        visible_status_filter = (
            Q(status=active_status)
            | Q(status=cancelled_status, cancelled_by__isnull=True)
            | (Q(status=cancelled_status) & ~Q(cancelled_by=user))
        )

        return (
            Booking.objects.filter(
                user=user,
                end_time__gte=timezone.now(),
            )
            .filter(visible_status_filter)
            .select_related("user", "resource", "resource__room", "resource__room__floor", "status", "cancelled_by")
            .order_by("start_time")
        )

    def cancel_booking(self, user, booking_id) -> Booking:
        """Скасовує бронювання користувача з відправкою сповіщення у разі скасування іншою особою.

        Args:
            user: Користувач, який здійснює скасування.
            booking_id: Ідентифікатор бронювання.

        Returns:
            Booking: Скасоване бронювання.
        """
        try:
            booking = Booking.objects.select_related(
                "user",
                "resource",
                "resource__room",
                "resource__room__floor",
                "status",
                "cancelled_by",
            ).get(id=booking_id)
        except Booking.DoesNotExist as exc:
            raise BookingNotFoundError("Бронювання з таким id не знайдено.") from exc

        if not self.can_cancel_booking(user, booking):
            raise BookingPermissionDeniedError("У вас немає прав для скасування цього бронювання.")

        cancelled_status = self.get_status("CANCELLED")
        if booking.status_id != cancelled_status.id:

            with transaction.atomic():
                booking.status = cancelled_status
                booking.cancelled_by = user
                booking.save(update_fields=["status", "cancelled_by"])

                # Якщо скасування зробив адміністратор або модератор (не сам власник), відправляємо сповіщення
                if user.id != booking.user.id:
                    start_str = timezone.localtime(booking.start_time).strftime("%d.%m.%Y %H:%M")
                    subject = f"Скасування бронювання: {booking.resource.name}"
                    message = (
                        f"Користувач {user.full_name} скасував ваше бронювання ресурсу '{booking.resource.name}', "
                        f"яке було заплановано на {start_str}.\n\n"
                        f"За питаннями звертайтеся за адресою: {user.email}"
                    )
                    self._send_system_announcement(user, [booking.user], subject, message)

        return booking

    def update_booking_time(self, user, booking_id, validated_data) -> Booking:
        """Змінює час існуючого бронювання з перевіркою конфліктів.

        Args:
            user: Користувач, який редагує бронювання.
            booking_id: Ідентифікатор бронювання.
            validated_data: Нові часові рамки.

        Returns:
            Booking: Оновлене бронювання.
        """
        new_start = validated_data["start_time"]
        new_end = validated_data["end_time"]

        with transaction.atomic():
            try:
                booking = (
                    Booking.objects.select_for_update()
                    .select_related("user", "resource", "resource__room", "resource__room__floor", "status")
                    .get(id=booking_id)
                )
            except Booking.DoesNotExist as exc:
                raise BookingNotFoundError("Бронювання з таким id не знайдено.") from exc

            if not user.is_admin and booking.user.id != user.id:
                raise BookingPermissionDeniedError("У вас немає прав для редагування цього бронювання.")

            if booking.status.status != "ACTIVE":
                raise BookingValidationError("Редагувати можна лише активні бронювання.")

            if booking.resource.is_blocked:
                raise BookingValidationError("Цей ресурс наразі заблокований.")

            active_status = self.get_status("ACTIVE")
            overlapping_bookings_count = (
                Booking.objects.filter(
                    resource=booking.resource,
                    status=active_status,
                    start_time__lt=new_end,
                    end_time__gt=new_start,
                )
                .exclude(id=booking.id)
                .select_for_update()
                .count()
            )

            if overlapping_bookings_count >= booking.resource.max_person:
                raise BookingValidationError("На обраний час ресурс уже повністю зайнятий кимось іншим.")

            booking.start_time = new_start
            booking.end_time = new_end
            booking.save(update_fields=["start_time", "end_time"])

        return booking

    def block_resource(self, user, resource_id):
        """Блокує ресурс для використання та автоматично скасовує всі активні бронювання на нього.

        Args:
            user: Користувач-адміністратор.
            resource_id: Ідентифікатор ресурсу.

        Returns:
            tuple: Об'єкт ресурсу та кількість скасованих бронювань.
        """
        if not user.is_admin:
            raise BookingPermissionDeniedError("Тільки адміністратор може блокувати ресурси.")

        with transaction.atomic():
            resource = self.get_resource_for_update(resource_id)
            resource.is_blocked = True
            resource.save(update_fields=["is_blocked"])

            cancelled_count = self.cancel_active_resource_bookings(resource, actor=user)

        return resource, cancelled_count

    def unblock_resource(self, user, resource_id) -> Resource:
        """Розблоковує ресурс для подальшого бронювання.

        Args:
            user: Користувач-адміністратор.
            resource_id: Ідентифікатор ресурсу.

        Returns:
            Resource: Розблокований ресурс.
        """
        if not user.is_admin:
            raise BookingPermissionDeniedError("Тільки адміністратор може розблоковувати ресурси.")

        with transaction.atomic():
            resource = self.get_resource_for_update(resource_id)
            resource.is_blocked = False
            resource.save(update_fields=["is_blocked"])

        return resource

    def cancel_active_resource_bookings(self, resource, actor=None) -> int:
        """Автоматично скасовує всі майбутні активні бронювання для вказаного ресурсу.

        Args:
            resource: Об'єкт ресурсу.
            actor: Користувач, який ініціював скасування (наприклад, адміністратор).

        Returns:
            int: Кількість скасованих бронювань.
        """
        active_status = self.get_status("ACTIVE")
        cancelled_status = self.get_status("CANCELLED")

        bookings_to_cancel = Booking.objects.filter(
            resource=resource,
            status=active_status,
            end_time__gt=timezone.now(),
        ).select_related("user")

        users_to_notify = list({b.user for b in bookings_to_cancel if actor and b.user.id != actor.id})

        update_data = {"status": cancelled_status}
        if actor:
            update_data["cancelled_by"] = actor

        count = bookings_to_cancel.update(**update_data)

        if actor and users_to_notify:
            subject = f"Увага: Ресурс '{resource.name}' заблоковано"
            message = (
                f"Користувач {actor.full_name} заблокував ресурс '{resource.name}'. "
                f"Усі ваші майбутні бронювання на цей ресурс було автоматично скасовано.\n\n"
                f"За питаннями звертайтеся за адресою: {actor.email}"
            )
            self._send_system_announcement(actor, users_to_notify, subject, message)

        return count

    def can_cancel_booking(self, user, booking) -> bool:
        """Перевіряє, чи має користувач права на скасування конкретного бронювання."""
        if user.is_admin or booking.user_id == user.id:
            return True

        return bool(user.is_moderator and self.get_user_floor_id(user) == booking.resource.room.floor_id)

    def get_booking(self, booking_id) -> Booking:
        """Отримує об'єкт бронювання за його ідентифікатором."""
        try:
            return Booking.objects.select_related(
                "user", "resource", "resource__room", "resource__room__floor", "status", "cancelled_by"
            ).get(id=booking_id)
        except Booking.DoesNotExist as exc:
            raise BookingNotFoundError("Бронювання з таким id не знайдено.") from exc

    def get_resource(self, resource_id) -> Resource:
        """Отримує об'єкт ресурсу за його ідентифікатором."""
        try:
            return Resource.objects.select_related("room", "room__floor").get(id=resource_id)
        except Resource.DoesNotExist as exc:
            raise BookingNotFoundError("Ресурс з таким id не знайдено.") from exc

    def get_resource_for_update(self, resource_id) -> Resource:
        """Отримує об'єкт ресурсу та блокує рядок у БД для оновлення."""
        try:
            return Resource.objects.select_for_update().select_related("room", "room__floor").get(id=resource_id)
        except Resource.DoesNotExist as exc:
            raise BookingNotFoundError("Ресурс з таким id не знайдено.") from exc

    def get_status(self, status_name) -> BookingStatus:
        """Отримує об'єкт статусу бронювання за його назвою (ACTIVE, CANCELLED)."""
        try:
            return BookingStatus.objects.get(status=status_name)
        except BookingStatus.DoesNotExist as exc:
            raise BookingStatusNotFoundError(f"Статус бронювання {status_name} не знайдено в базі даних.") from exc

    def get_user_floor_id(self, user):
        """Повертає ідентифікатор поверху користувача."""
        if user.room_id:
            return user.room.floor_id

        return None

    def _send_system_announcement(self, actor, target_users, title, message):
        """Створює внутрішнє системне оголошення для групи користувачів."""
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
            raise BookingError("Не вдалося надіслати сповіщення користувачам. Дію скасовано.") from exc
