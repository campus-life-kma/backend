from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from django.utils.dateparse import parse_date

from api.models import Booking, BookingStatus, Resource


class BookingError(Exception):
    default_detail = "Сталася помилка бронювання."

    def __init__(self, detail=None):
        super().__init__(detail or self.default_detail)


class BookingNotFoundError(BookingError):
    default_detail = "Об'єкт не знайдено."


class BookingPermissionDeniedError(BookingError):
    default_detail = "У вас немає прав для цієї дії."


class BookingValidationError(BookingError):
    default_detail = "Бронювання неможливо виконати."


class BookingStatusNotFoundError(BookingError):
    default_detail = "Потрібний статус бронювання не знайдено в базі даних."


class BookingsService:
    def get_resource_schedule(self, resource_id, start_date_str=None, end_date_str=None):
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
            .select_related("status")
            .order_by("start_time")
        )

    def _parse_date_range(self, start_date_str, end_date_str):
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

        start_range = timezone.make_aware(datetime.combine(start_date, time.min), current_timezone)
        end_range = timezone.make_aware(datetime.combine(end_date, time.max), current_timezone)

        return start_range, end_range

    def create_booking(self, user, validated_data):
        resource_id = validated_data["resource"].id
        start_time = validated_data["start_time"]
        end_time = validated_data["end_time"]

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
        active_status = self.get_status("ACTIVE")
        cancelled_status = self.get_status("CANCELLED")
        return (
            Booking.objects.filter(
                user=user,
                status__in=[active_status, cancelled_status],
                end_time__gte=timezone.now(),
            )
            .select_related("user", "resource", "resource__room", "resource__room__floor", "status")
            .order_by("start_time")
        )

    def cancel_booking(self, user, booking_id):
        try:
            booking = Booking.objects.select_related(
                "user",
                "resource",
                "resource__room",
                "resource__room__floor",
                "status",
            ).get(id=booking_id)
        except Booking.DoesNotExist as exc:
            raise BookingNotFoundError("Бронювання з таким id не знайдено.") from exc

        if not self.can_cancel_booking(user, booking):
            raise BookingPermissionDeniedError("У вас немає прав для скасування цього бронювання.")

        cancelled_status = self.get_status("CANCELLED")
        if booking.status_id != cancelled_status.id:
            booking.status = cancelled_status
            booking.save(update_fields=["status"])

        return booking

    def update_booking_time(self, user, booking_id, validated_data):
        new_start = validated_data["start_time"]
        new_end = validated_data["end_time"]

        with transaction.atomic():
            try:
                booking = Booking.objects.select_for_update().select_related("resource").get(id=booking_id)
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
        if not user.is_admin:
            raise BookingPermissionDeniedError("Тільки адміністратор може блокувати ресурси.")

        with transaction.atomic():
            resource = self.get_resource_for_update(resource_id)
            resource.is_blocked = True
            resource.save(update_fields=["is_blocked"])

            cancelled_count = self.cancel_active_resource_bookings(resource)

        return resource, cancelled_count

    def unblock_resource(self, user, resource_id):
        if not user.is_admin:
            raise BookingPermissionDeniedError("Тільки адміністратор може розблоковувати ресурси.")

        with transaction.atomic():
            resource = self.get_resource_for_update(resource_id)
            resource.is_blocked = False
            resource.save(update_fields=["is_blocked"])

        return resource

    def cancel_active_resource_bookings(self, resource):
        active_status = self.get_status("ACTIVE")
        cancelled_status = self.get_status("CANCELLED")

        return Booking.objects.filter(
            resource=resource,
            status=active_status,
            end_time__gt=timezone.now(),
        ).update(status=cancelled_status)

    def can_cancel_booking(self, user, booking):
        if user.is_admin or booking.user_id == user.id:
            return True

        return bool(user.is_moderator and self.get_user_floor_id(user) == booking.resource.room.floor_id)

    def get_resource(self, resource_id):
        try:
            return Resource.objects.select_related("room", "room__floor").get(id=resource_id)
        except Resource.DoesNotExist as exc:
            raise BookingNotFoundError("Ресурс з таким id не знайдено.") from exc

    def get_resource_for_update(self, resource_id):
        try:
            return Resource.objects.select_for_update().select_related("room", "room__floor").get(id=resource_id)
        except Resource.DoesNotExist as exc:
            raise BookingNotFoundError("Ресурс з таким id не знайдено.") from exc

    def get_status(self, status_name):
        try:
            return BookingStatus.objects.get(status=status_name)
        except BookingStatus.DoesNotExist as exc:
            raise BookingStatusNotFoundError(f"Статус бронювання {status_name} не знайдено в базі даних.") from exc

    def get_user_floor_id(self, user):
        if user.room_id:
            return user.room.floor_id

        return None
