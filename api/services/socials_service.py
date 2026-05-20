from django.db import transaction
from django.utils import timezone

from api.models import SocialEvent, SocialSharingRequest, SocialSharingStatus


class SocialsService:
    page_size = 20

    def get_feed(self, user, page):
        page = max(page, 1)
        now = timezone.now()

        events = (
            SocialEvent.objects.filter(start_time__gte=now)
            .select_related("creator", "creator__major", "creator__major__faculty", "room", "room__floor", "floor")
            .prefetch_related("participants")
        )
        sharing_requests = (
            SocialSharingRequest.objects.filter(status__status="ACTIVE")
            .select_related("creator", "creator__room", "creator__room__floor", "status")
            .order_by("-created_at")
        )

        visible_events = [event for event in events if self.can_view_event(user, event)]
        items = [(event.start_time, "event", event) for event in visible_events]
        items.extend((request.created_at, "sharing_request", request) for request in sharing_requests)
        items.sort(key=lambda item: item[0], reverse=True)

        start = (page - 1) * self.page_size
        end = start + self.page_size
        page_items = items[start:end]

        return {
            "page": page,
            "page_size": self.page_size,
            "has_next": len(items) > end,
            "items": page_items,
        }

    def create_event(self, user, validated_data):
        event = SocialEvent.objects.create(creator=user, **validated_data)
        event.participants.add(user)
        return event

    def join_event(self, user, event_id):
        now = timezone.now()

        with transaction.atomic():
            try:
                event = SocialEvent.objects.select_for_update().get(id=event_id)
            except SocialEvent.DoesNotExist as exc:
                raise ValueError("Подію з таким id не знайдено.") from exc

            if event.end_time < now:
                raise ValueError("Неможливо приєднатися до події, яка вже завершилася.")

            if not self.can_view_event(user, event):
                raise ValueError("Ви не маєте доступу до цієї події.")

            if event.participants.filter(id=user.id).exists():
                return event

            if event.max_person > 0 and event.participants.count() >= event.max_person:
                raise ValueError("На цю подію вже немає вільних місць.")

            event.participants.add(user)

        return event

    def leave_event(self, user, event_id):
        try:
            event = SocialEvent.objects.prefetch_related("participants").get(id=event_id)
        except SocialEvent.DoesNotExist as exc:
            raise ValueError("Подію з таким id не знайдено.") from exc

        event.participants.remove(user)
        return event

    def delete_event(self, user, event_id):
        try:
            event = SocialEvent.objects.select_related("creator", "room", "room__floor", "floor").get(id=event_id)
        except SocialEvent.DoesNotExist as exc:
            raise ValueError("Подію з таким id не знайдено.") from exc

        if not self.can_manage_event(user, event):
            raise ValueError("Ви не маєте прав для видалення цієї події.")

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
            raise ValueError("Запит на шеринг з таким id не знайдено.") from exc

        if not self.can_manage_sharing_request(user, sharing_request):
            raise ValueError("Ви не маєте прав для завершення цього запиту.")

        sharing_request.status = self.get_status("COMPLETED")
        sharing_request.save(update_fields=["status"])
        return sharing_request

    def delete_sharing_request(self, user, request_id):
        try:
            sharing_request = SocialSharingRequest.objects.select_related(
                "creator", "creator__room", "creator__room__floor", "status"
            ).get(id=request_id)
        except SocialSharingRequest.DoesNotExist as exc:
            raise ValueError("Запит на шеринг з таким id не знайдено.") from exc

        if not self.can_manage_sharing_request(user, sharing_request):
            raise ValueError("Ви не маєте прав для видалення цього запиту.")

        sharing_request.status = self.get_status("CANCELLED")
        sharing_request.save(update_fields=["status"])
        return sharing_request

    def get_status(self, status_name):
        try:
            return SocialSharingStatus.objects.get(status=status_name)
        except SocialSharingStatus.DoesNotExist as exc:
            raise ValueError(f"Статус {status_name} не знайдено в базі даних.") from exc

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
