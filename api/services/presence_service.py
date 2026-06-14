from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from api.models import Presence, Room


class PresenceService:
    """Сервіс для керування присутністю користувачів у кімнатах гуртожитку."""

    def check_in(self, user, room_id) -> Presence:
        """Реєструє присутність користувача в кімнаті.

        Args:
            user: Об'єкт користувача, який реєструється.
            room_id: Ідентифікатор кімнати.

        Returns:
            Presence: Створений або оновлений запис присутності.

        Raises:
            ValueError: Якщо кімнату не знайдено або вона заблокована.
        """
        try:
            room = Room.objects.select_related("room_type").get(id=room_id)
        except Room.DoesNotExist as exc:
            raise ValueError("Кімнату з таким id не знайдено.") from exc

        if room.is_blocked:
            raise ValueError("Ця кімната заблокована, тому в ній не можна відмітити присутність.")

        now = timezone.now()

        # Використовуємо транзакцію для атомарного оновлення або створення запису присутності
        with transaction.atomic():
            presence, _ = Presence.objects.update_or_create(
                user=user,
                defaults={
                    "room": room,
                    "joined_at": now,
                    "expires_at": now + timedelta(hours=2),  # Час перебування обмежено 2 годинами
                },
            )

        return presence

    def go_home(self, user) -> int:
        """Видаляє запис про присутність користувача (позначає, що він пішов).

        Args:
            user: Об'єкт користувача.

        Returns:
            int: Кількість видалених записів.
        """
        deleted_count, _ = Presence.objects.filter(user=user).delete()
        return deleted_count

    def get_current(self, user):
        """Повертає активний запис присутності користувача, якщо термін його дії не закінчився.

        Args:
            user: Об'єкт користувача.

        Returns:
            Presence: Об'єкт присутності або None.
        """
        now = timezone.now()
        return Presence.objects.select_related("room", "room__floor").filter(user=user, expires_at__gt=now).first()
