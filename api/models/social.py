from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, CheckConstraint
from django.core.exceptions import ValidationError
from django.conf import settings


class SocialEvent(models.Model):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_events",
        help_text="Організатор івенту",
    )
    status = models.ForeignKey(
        "SocialSharingStatus",
        on_delete=models.PROTECT,
        related_name="events",
        help_text="Поточний статус івенту",
    )
    room = models.ForeignKey(
        "Room",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="events",
        help_text="Кімната, де відбудеться івент (якщо локація прив'язана до конкретної кімнати)",
    )
    floor = models.ForeignKey(
        "Floor",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="events",
        help_text="Поверх, де відбудеться івент (наприклад, у спільному холі)",
    )

    custom_location = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Власна назва локації, якщо це не кімната і не поверх (наприклад, 'Кухня 3-го поверху', 'Подвір'я')",
    )

    title = models.CharField(max_length=255, help_text="Коротка назва заходу (наприклад, 'Вечір настільних ігор')")
    description = models.TextField(
        null=True, blank=True, help_text="Детальний опис: що буде відбуватись, що варто взяти з собою тощо"
    )
    start_time = models.DateTimeField(help_text="Запланований час початку івенту")
    end_time = models.DateTimeField(help_text="Орієнтовний час завершення івенту")
    max_person = models.IntegerField(
        validators=[MinValueValidator(0)], help_text="Максимальна кількість учасників. Якщо 0 — кількість не обмежена"
    )

    is_faculty_only = models.BooleanField(
        default=False,
        help_text="Якщо True, івент бачитимуть і зможуть приєднатися лише студенти факультету організатора",
    )
    is_major_only = models.BooleanField(
        default=False, help_text="Якщо True, івент доступний лише для студентів спеціальності організатора"
    )

    created_at = models.DateTimeField(auto_now_add=True, help_text="Точний час створення запиту")

    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="participating_events",
        blank=True,
        help_text="Список мешканців, які підтвердили свою участь",
    )

    class Meta:
        constraints = [
            CheckConstraint(
                condition=Q(room__isnull=False) | Q(floor__isnull=False) | Q(custom_location__isnull=False),
                name="event_must_have_location",
            )
        ]

    def clean(self):
        super().clean()
        if not self.room and not self.floor and not self.custom_location:
            raise ValidationError(
                "Будь ласка, вкажіть хоча б одне місце проведення івенту: кімнату, поверх або кастомну локацію."
            )

    def __str__(self):
        return f"{self.title} (Організатор: {self.creator.email})"


class SocialSharingStatus(models.Model):
    status = models.CharField(
        max_length=100, unique=True, help_text="Системна назва статусу (наприклад, 'ACTIVE', 'CANCELLED', 'COMPLETED')"
    )

    def __str__(self):
        return self.status


class SocialSharingRequest(models.Model):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sharing_requests",
        help_text="Студент, який створив запит (наприклад, шукає праску або сіль)",
    )
    title = models.CharField(
        max_length=255, help_text="Короткий зміст того, що потрібно (наприклад, 'Позичте праску на годину')"
    )

    created_at = models.DateTimeField(auto_now_add=True, help_text="Точний час створення запиту")

    status = models.ForeignKey(
        SocialSharingStatus,
        on_delete=models.PROTECT,
        related_name="requests",
        help_text="Поточний стан запиту (актуальний чи вже закритий)",
    )

    def __str__(self):
        return f"[{self.status.status}] {self.title} (Автор: {self.creator.email})"
