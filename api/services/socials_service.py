from datetime import datetime, time

from django.db import transaction
from django.db.models import Count, F, Q, Value
from django.db.models.fields import CharField
from django.utils import timezone
from django.utils.dateparse import parse_date

from api.models import SocialEvent, SocialSharingRequest, SocialSharingStatus


class SocialError(Exception):
    default_detail = "Сталася помилка соціальної стрічки."

    def __init__(self, detail=None):
        super().__init__(detail or self.default_detail)


class SocialNotFoundError(SocialError):
    default_detail = "Об'єкт не знайдено."


class SocialPermissionDeniedError(SocialError):
    default_detail = "У вас немає прав для цієї дії."


class SocialAccessDeniedError(SocialError):
    default_detail = "Ви не маєте доступу до цієї події."


class SocialEventFullError(SocialError):
    default_detail = "На цю подію вже немає вільних місць."


class SocialEventUnavailableError(SocialError):
    default_detail = "Неможливо приєднатися до події, яка вже завершилася."


class SocialStatusNotFoundError(SocialError):
    default_detail = "Потрібний статус не знайдено в базі даних."


class SocialsService:
    page_size = 20

    def get_feed(self, user, page, filters: dict):
        page = max(page, 1)
        now = timezone.now()

        start = (page - 1) * self.page_size
        end = start + self.page_size

        rows = list(self.get_feed_rows(user, now, filters)[start : end + 1])
        page_rows = rows[: self.page_size]

        return {
            "page": page,
            "page_size": self.page_size,
            "has_next": len(rows) > self.page_size,
            "items": self.resolve_feed_items(page_rows),
        }

    def get_feed_rows(self, user, now, filters: dict):
        item_type = filters.get("item_type", "all")
        ordering = filters.get("ordering", "created_at")

        event_sort_field = "start_time" if ordering == "start_time" else "created_at"
        sharing_sort_field = "created_at"

        event_rows = None
        sharing_rows = None

        if item_type in ["all", "event"]:
            event_rows = self._get_event_rows(user, now, filters, event_sort_field)

        if item_type in ["all", "sharing_request"]:
            sharing_rows = self._get_sharing_rows(user, filters, sharing_sort_field)

        if event_rows is not None and sharing_rows is not None:
            combined = event_rows.union(sharing_rows, all=True)
        elif event_rows is not None:
            combined = event_rows
        elif sharing_rows is not None:
            combined = sharing_rows
        else:
            return SocialEvent.objects.none()

        if ordering == "start_time":
            return combined.order_by("sort_time")
        return combined.order_by("-sort_time")

    def _get_event_rows(self, user, now, filters: dict, sort_field: str):
        events_qs = self.get_visible_events_queryset(user, now)

        if filters.get("start_date") or filters.get("end_date"):
            start_dt, end_dt = self._parse_date_bounds(filters.get("start_date"), filters.get("end_date"))
            if start_dt:
                events_qs = events_qs.filter(start_time__gte=start_dt)
            if end_dt:
                events_qs = events_qs.filter(start_time__lte=end_dt)

        if filters.get("is_active"):
            events_qs = events_qs.filter(start_time__lte=now, end_time__gte=now)

        floor_filter = filters.get("floor_id")
        if floor_filter:
            target_floor_id = user.room.floor_id if floor_filter == "my" else floor_filter
            if target_floor_id:
                events_qs = events_qs.filter(Q(floor_id=target_floor_id) | Q(room__floor_id=target_floor_id))

        return events_qs.annotate(
            item_type=Value("event", output_field=CharField()),
            item_id=F("id"),
            sort_time=F(sort_field),
        ).values("item_type", "item_id", "sort_time")

    def _get_sharing_rows(self, user, filters: dict, sort_field: str):
        sharing_qs = SocialSharingRequest.objects.filter(status__status="ACTIVE")

        floor_filter = filters.get("floor_id")
        if floor_filter:
            target_floor_id = user.room.floor_id if floor_filter == "my" else floor_filter
            if target_floor_id:
                sharing_qs = sharing_qs.filter(creator__room__floor_id=target_floor_id)

        return sharing_qs.annotate(
            item_type=Value("sharing_request", output_field=CharField()),
            item_id=F("id"),
            sort_time=F(sort_field),
        ).values("item_type", "item_id", "sort_time")

    def _parse_date_bounds(self, start_str, end_str):
        current_timezone = timezone.get_current_timezone()
        start_dt, end_dt = None, None

        if start_str:
            p_date = parse_date(start_str)
            if p_date:
                start_dt = timezone.make_aware(datetime.combine(p_date, time.min), current_timezone)
        if end_str:
            p_date = parse_date(end_str)
            if p_date:
                end_dt = timezone.make_aware(datetime.combine(p_date, time.max), current_timezone)

        return start_dt, end_dt

    def get_visible_events_queryset(self, user, now):
        user_faculty_id = self.get_faculty_id(user)

        return (
            SocialEvent.objects.filter(end_time__gte=now)
            .filter(Q(is_faculty_only=False) | Q(creator__major__faculty_id=user_faculty_id))
            .filter(Q(is_major_only=False) | Q(creator__major_id=user.major_id))
        )

    def resolve_feed_items(self, rows):
        event_ids = [row["item_id"] for row in rows if row["item_type"] == "event"]
        sharing_request_ids = [row["item_id"] for row in rows if row["item_type"] == "sharing_request"]
        events = (
            SocialEvent.objects.select_related(
                "creator",
                "creator__major",
                "creator__major__faculty",
                "room",
                "room__floor",
                "floor",
            )
            .prefetch_related("participants")
            .annotate(participants_count=Count("participants"))
            .in_bulk(event_ids)
        )
        sharing_requests = SocialSharingRequest.objects.select_related(
            "creator",
            "creator__room",
            "creator__room__floor",
            "status",
        ).in_bulk(sharing_request_ids)

        items = []
        for row in rows:
            if row["item_type"] == "event":
                item = events.get(row["item_id"])
            else:
                item = sharing_requests.get(row["item_id"])

            if item:
                items.append((row["sort_time"], row["item_type"], item))

        return items

    def create_event(self, user, validated_data):
        event = SocialEvent.objects.create(creator=user, **validated_data)
        event.participants.add(user)
        return event

    def get_event_detail(self, user, event_id):
        try:
            event = (
                SocialEvent.objects.select_related(
                    "creator",
                    "creator__major",
                    "creator__major__faculty",
                    "room",
                    "room__floor",
                    "floor",
                )
                .prefetch_related("participants")
                .get(id=event_id)
            )
        except SocialEvent.DoesNotExist as exc:
            raise SocialNotFoundError("Подію з таким id не знайдено.") from exc

        if not self.can_view_event(user, event):
            raise SocialAccessDeniedError()

        return event

    def get_sharing_request_detail(self, user, request_id):
        try:
            return SocialSharingRequest.objects.select_related(
                "creator", "creator__room", "creator__room__floor", "status"
            ).get(id=request_id)
        except SocialSharingRequest.DoesNotExist as exc:
            raise SocialNotFoundError("Запит на шеринг з таким id не знайдено.") from exc

    def join_event(self, user, event_id):
        now = timezone.now()

        with transaction.atomic():
            try:
                event = SocialEvent.objects.select_for_update().get(id=event_id)
            except SocialEvent.DoesNotExist as exc:
                raise SocialNotFoundError("Подію з таким id не знайдено.") from exc

            if event.end_time < now:
                raise SocialEventUnavailableError()

            if not self.can_view_event(user, event):
                raise SocialAccessDeniedError()

            if event.participants.filter(id=user.id).exists():
                return event

            if event.max_person > 0 and event.participants.count() >= event.max_person:
                raise SocialEventFullError()

            event.participants.add(user)

        return event

    def leave_event(self, user, event_id):
        try:
            event = SocialEvent.objects.prefetch_related("participants").get(id=event_id)
        except SocialEvent.DoesNotExist as exc:
            raise SocialNotFoundError("Подію з таким id не знайдено.") from exc

        event.participants.remove(user)
        return event

    def delete_event(self, user, event_id):
        try:
            event = SocialEvent.objects.select_related("creator", "room", "room__floor", "floor").get(id=event_id)
        except SocialEvent.DoesNotExist as exc:
            raise SocialNotFoundError("Подію з таким id не знайдено.") from exc

        if not self.can_manage_event(user, event):
            raise SocialPermissionDeniedError("Ви не маєте прав для видалення цієї події.")

        event.delete()

    def create_sharing_request(self, user, validated_data):
        status = self.get_status("ACTIVE")
        return SocialSharingRequest.objects.create(creator=user, status=status, **validated_data)

    def complete_sharing_request(self, user, request_id):
        try:
            sharing_request = SocialSharingRequest.objects.select_related(
                "creator", "creator__room", "creator__room__floor", "status"
            ).get(id=request_id)
        except SocialSharingRequest.DoesNotExist as exc:
            raise SocialNotFoundError("Запит на шеринг з таким id не знайдено.") from exc

        if not self.can_manage_sharing_request(user, sharing_request):
            raise SocialPermissionDeniedError("Ви не маєте прав для завершення цього запиту.")

        sharing_request.status = self.get_status("COMPLETED")
        sharing_request.save(update_fields=["status"])
        return sharing_request

    def delete_sharing_request(self, user, request_id):
        try:
            sharing_request = SocialSharingRequest.objects.select_related(
                "creator", "creator__room", "creator__room__floor", "status"
            ).get(id=request_id)
        except SocialSharingRequest.DoesNotExist as exc:
            raise SocialNotFoundError("Запит на шеринг з таким id не знайдено.") from exc

        if not self.can_manage_sharing_request(user, sharing_request):
            raise SocialPermissionDeniedError("Ви не маєте прав для видалення цього запиту.")

        sharing_request.status = self.get_status("CANCELLED")
        sharing_request.save(update_fields=["status"])
        return sharing_request

    def get_status(self, status_name):
        try:
            return SocialSharingStatus.objects.get(status=status_name)
        except SocialSharingStatus.DoesNotExist as exc:
            raise SocialStatusNotFoundError(f"Статус {status_name} не знайдено в базі даних.") from exc

    def can_view_event(self, user, event):
        if event.is_faculty_only and self.get_faculty_id(user) != self.get_faculty_id(event.creator):
            return False

        if event.is_major_only and user.major_id != event.creator.major_id:
            return False

        return True

    def can_manage_event(self, user, event):
        if event.creator_id == user.id or user.is_admin:
            return True

        event_floor_id = self.get_event_floor_id(event)
        return self.can_moderate_floor(user, event_floor_id)

    def can_manage_sharing_request(self, user, sharing_request):
        if sharing_request.creator_id == user.id or user.is_admin:
            return True

        request_floor_id = self.get_user_floor_id(sharing_request.creator)
        return self.can_moderate_floor(user, request_floor_id)

    def can_moderate_floor(self, user, floor_id):
        return bool(user.is_moderator and floor_id and self.get_user_floor_id(user) == floor_id)

    def get_event_floor_id(self, event):
        if event.floor_id:
            return event.floor_id

        if event.room_id:
            return event.room.floor_id

        return None

    def get_user_floor_id(self, user):
        if user.room_id:
            return user.room.floor_id

        return None

    def get_faculty_id(self, user):
        if user.major_id:
            return user.major.faculty_id

        return None
