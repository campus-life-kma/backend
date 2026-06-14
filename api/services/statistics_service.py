from django.db.models import Count, F, Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from api.models import (
    Announcement,
    Booking,
    Floor,
    Presence,
    Resource,
    Room,
    SocialEvent,
    SocialSharingRequest,
    User,
)


class StatisticsService:
    """Сервіс збору та аналізу статистичних даних по гуртожитку або конкретному поверху."""

    def get_summary(self, user: User) -> dict:
        """Повертає загальний звіт про роботу гуртожитку на основі ролі користувача.

        Args:
            user: Користувач, який запитує статистику.

        Returns:
            dict: Звіт зі статистичними даними.

        Raises:
            PermissionDenied: Якщо користувач не має прав доступу (не адмін і не модератор).
        """
        if user.is_admin:
            return self.get_admin_summary(user)

        if user.is_moderator:
            return self.get_moderator_summary(user)

        raise PermissionDenied(detail="Статистика доступна лише адміністраторам і модераторам.")

    def get_admin_summary(self, user: User) -> dict:
        """Формує статистичний звіт для адміністратора по всьому гуртожитку.

        Args:
            user: Об'єкт адміністратора.

        Returns:
            dict: Дані статистики гуртожитку.
        """
        dormitory = user.room.floor.dormitory if user.room_id else None
        floors = Floor.objects.all()
        if dormitory:
            floors = floors.filter(dormitory=dormitory)

        return self.build_summary(user=user, floors=floors, scope_type="DORMITORY")

    def get_moderator_summary(self, user: User) -> dict:
        """Формує статистичний звіт для модератора конкретного поверху.

        Args:
            user: Об'єкт модератора поверху.

        Returns:
            dict: Дані статистики поверху.
        """
        if not user.room_id:
            raise ValidationError(
                {"detail": "Модератор не прив'язаний до кімнати, тому поверх для статистики невідомий."}
            )

        floors = Floor.objects.filter(id=user.room.floor_id)
        return self.build_summary(user=user, floors=floors, scope_type="FLOOR")

    def build_summary(self, user: User, floors, scope_type: str) -> dict:
        """Формує консолідований звіт по мешканцях, кімнатах, бронюваннях та активностях.

        Args:
            user: Користувач, який запитує звіт.
            floors: QuerySet поверхів, що входять в область перегляду.
            scope_type: Масштаб звіту ("DORMITORY" або "FLOOR").

        Returns:
            dict: Словник з підрахованими показниками.
        """
        floor_ids = list(floors.values_list("id", flat=True))
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timezone.timedelta(days=1)

        # Збираємо вибірки за ідентифікаторами поверхів
        users = User.objects.filter(room__floor_id__in=floor_ids)
        rooms = Room.objects.filter(floor_id__in=floor_ids)
        resources = Resource.objects.filter(room__floor_id__in=floor_ids)
        bookings = Booking.objects.filter(resource__room__floor_id__in=floor_ids)
        events = SocialEvent.objects.filter(Q(floor_id__in=floor_ids) | Q(room__floor_id__in=floor_ids)).distinct()
        sharing_requests = SocialSharingRequest.objects.filter(creator__room__floor_id__in=floor_ids)
        presences = Presence.objects.filter(room__floor_id__in=floor_ids, expires_at__gt=now)
        announcements = self.get_announcements_for_scope(user=user, floor_ids=floor_ids, scope_type=scope_type)

        active_booking_filter = Q(status__status="ACTIVE")
        cancelled_booking_filter = Q(status__status="CANCELLED")
        active_social_filter = Q(status__status="ACTIVE")
        cancelled_social_filter = Q(status__status="CANCELLED")

        result = {
            "scope": self.build_scope(user=user, floors=floors, scope_type=scope_type),
            "residents": {
                "total": users.count(),
                "activated": users.filter(is_activated=True).count(),
                "not_activated": users.filter(is_activated=False).count(),
                "moderators": users.filter(role__name="MODERATOR").count(),
            },
            "rooms": {
                "total": rooms.count(),
                "living": rooms.filter(room_type__type="LIVING").count(),
                "blocked": rooms.filter(is_blocked=True).count(),
                "full": self.count_full_rooms(rooms),
            },
            "resources": {
                "total": resources.count(),
                "blocked": resources.filter(is_blocked=True).count(),
            },
            "bookings": {
                "active": bookings.filter(active_booking_filter).count(),
                "today": bookings.filter(
                    active_booking_filter,
                    start_time__lt=tomorrow_start,
                    end_time__gt=today_start,
                ).count(),
                "cancelled": bookings.filter(cancelled_booking_filter).count(),
                "cancelled_by_residents": bookings.filter(
                    cancelled_booking_filter,
                    cancelled_by__role__name="RESIDENT",
                ).count(),
                "cancelled_by_moderators": bookings.filter(
                    cancelled_booking_filter,
                    cancelled_by__role__name="MODERATOR",
                ).count(),
                "cancelled_by_admins": bookings.filter(
                    cancelled_booking_filter,
                    cancelled_by__role__name="ADMIN",
                ).count(),
                "top_resources": self.get_top_resources(bookings),
            },
            "social": {
                "active_events": events.filter(active_social_filter, end_time__gt=now).count(),
                "cancelled_events": events.filter(cancelled_social_filter).count(),
                "active_sharing_requests": sharing_requests.filter(active_social_filter).count(),
                "completed_sharing_requests": sharing_requests.filter(status__status="COMPLETED").count(),
                "cancelled_sharing_requests": sharing_requests.filter(cancelled_social_filter).count(),
                "floor_activity": self.get_floor_activity(floors, now),
            },
            "announcements": {
                "active": announcements.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)).count(),
                "pinned": announcements.filter(is_pinned=True).count(),
                "total": announcements.count(),
            },
            "presence": {
                "active": presences.count(),
            },
        }

        if user.is_admin:
            moderators = User.objects.filter(role__name="MODERATOR", is_activated=True)
            moderator_actions = []
            for mod in moderators:
                moderator_actions.append({
                    "moderator_id": mod.id,
                    "moderator_name": mod.full_name or mod.email,
                    "cancelled_events": SocialEvent.objects.filter(cancelled_by=mod).count(),
                    "cancelled_sharings": SocialSharingRequest.objects.filter(cancelled_by=mod).count(),
                    "cancelled_bookings": Booking.objects.filter(cancelled_by=mod).count(),
                })
            result["moderator_actions"] = moderator_actions

        return result

    def build_scope(self, user: User, floors, scope_type: str) -> dict:
        """Будує метадані області перегляду статистики."""
        first_floor = floors.select_related("dormitory").order_by("number").first()
        return {
            "type": scope_type,
            "dormitory_name": first_floor.dormitory.name if first_floor else None,
            "floor_id": first_floor.id if scope_type == "FLOOR" and first_floor else None,
            "floor_number": first_floor.number if scope_type == "FLOOR" and first_floor else None,
            "role": user.role.name if user.role_id else None,
        }

    def count_full_rooms(self, rooms) -> int:
        """Рахує кількість повністю заселених житлових кімнат."""
        return (
            rooms.filter(room_type__type="LIVING")
            .annotate(residents_count=Count("user", filter=Q(user__is_activated=True)))
            .filter(residents_count__gte=F("max_person"))
            .count()
        )

    def get_top_resources(self, bookings) -> list[dict]:
        """Повертає топ-5 найбільш затребуваних ресурсів за кількістю бронювань."""
        rows = (
            bookings.values("resource_id", "resource__name", "resource__room__name", "resource__room__floor__number")
            .annotate(count=Count("id"))
            .order_by("-count", "resource__name")[:5]
        )
        return [
            {
                "resource_id": row["resource_id"],
                "resource_name": row["resource__name"],
                "room_name": row["resource__room__name"],
                "floor_number": row["resource__room__floor__number"],
                "bookings_count": row["count"],
            }
            for row in rows
        ]

    def get_floor_activity(self, floors, now) -> list[dict]:
        """Підраховує активність (івенти, шеринг, присутність) по кожному поверху."""
        data = []
        for floor in floors.order_by("number"):
            data.append(
                {
                    "floor_id": floor.id,
                    "floor_number": floor.number,
                    "residents_count": User.objects.filter(room__floor=floor, is_activated=True).count(),
                    "active_events_count": SocialEvent.objects.filter(
                        Q(floor=floor) | Q(room__floor=floor),
                        status__status="ACTIVE",
                        end_time__gt=now,
                    )
                    .distinct()
                    .count(),
                    "active_sharing_requests_count": SocialSharingRequest.objects.filter(
                        creator__room__floor=floor,
                        status__status="ACTIVE",
                    ).count(),
                    "active_presence_count": Presence.objects.filter(room__floor=floor, expires_at__gt=now).count(),
                }
            )
        return data

    def get_announcements_for_scope(self, user: User, floor_ids: list[int], scope_type: str):
        """Отримує оголошення, що відносяться до вказаної області видимості поверхів."""
        if scope_type == "DORMITORY":
            return Announcement.objects.filter(
                Q(target_type__type="GLOBAL")
                | Q(target_floor_id__in=floor_ids)
                | Q(target_room__floor_id__in=floor_ids)
                | Q(target_users__room__floor_id__in=floor_ids)
            ).distinct()

        return Announcement.objects.filter(
            Q(target_type__type="GLOBAL")
            | Q(target_floor_id__in=floor_ids)
            | Q(target_room__floor_id__in=floor_ids)
            | Q(target_users=user)
        ).distinct()
