from django.db import models
from django.conf import settings


class Presence(models.Model):
    """Модель фіксації тимчасової присутності мешканця у кімнатах загального користування."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="presences",
        help_text="Мешканець, який зараз перебуває у певній локації",
    )
    room = models.ForeignKey(
        "Room",
        on_delete=models.CASCADE,
        related_name="presences",
        help_text="Кімната або приміщення, де відмітився мешканець",
    )

    joined_at = models.DateTimeField(help_text="Фактичний час, коли користувач натиснув 'Я тут'")
    expires_at = models.DateTimeField(help_text="Час автоматичного скасування присутності")

    class Meta:
        constraints = [
            # Користувач може мати лише один активний запис присутності одночасно
            models.UniqueConstraint(fields=["user"], name="unique_presence_per_user"),
        ]
        indexes = [
            # Індекси для швидкого очищення застарілих записів та пошуку по кімнатах
            models.Index(fields=["expires_at"], name="presence_expires_at_idx"),
            models.Index(fields=["room", "expires_at"], name="presence_room_expires_idx"),
        ]

    def __str__(self):
        return f"{self.user.email} У {self.room.name}"


class BookingStatus(models.Model):
    """Словникова модель для можливих статусів бронювання (ACTIVE, CANCELLED)."""

    status = models.CharField(
        max_length=100,
        unique=True,
        help_text="Системна назва статусу бронювання (наприклад, 'ACTIVE', 'CANCELLED', 'COMPLETED')",
    )

    def __str__(self):
        return self.status


class Booking(models.Model):
    """Модель індивідуального бронювання ресурсів (наприклад, пральних машин або духових шаф)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
        help_text="Студент, який забронював ресурс",
    )
    resource = models.ForeignKey(
        "Resource",
        on_delete=models.CASCADE,
        related_name="bookings",
        help_text="Конкретний ресурс, що бронюється (наприклад, 'Пральна машина №2')",
    )

    start_time = models.DateTimeField(help_text="Час початку використання ресурсу")
    end_time = models.DateTimeField(help_text="Час завершення використання ресурсу")

    status = models.ForeignKey(
        BookingStatus, on_delete=models.PROTECT, related_name="bookings", help_text="Поточний стан цього бронювання"
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_bookings",
        help_text="Користувач, який скасував бронювання",
    )

    def __str__(self):
        return f"Бронювання: {self.resource.name} {self.user.email} ({self.start_time.strftime('%H:%M')})"
