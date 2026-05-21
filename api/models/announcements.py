from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings


class TargetType(models.Model):
    type = models.CharField(
        max_length=100,
        unique=True,
        help_text="Тип аудиторії, для якої призначене оголошення "
        "(наприклад, 'GLOBAL', 'FLOOR', 'ROOM', 'SPECIFIC_USERS')",
    )

    def __str__(self):
        return self.type


class Announcement(models.Model):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_announcements",
        help_text="Автор оголошення (зазвичай Адміністратор або Модератор)",
    )

    target_type = models.ForeignKey(
        TargetType,
        on_delete=models.PROTECT,
        related_name="announcements",
        help_text="Визначає масштаб аудиторії (кому саме буде показано це оголошення)",
    )

    target_floor = models.ForeignKey(
        "Floor",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="announcements",
        help_text="Оберіть поверх, якщо оголошення стосується лише його мешканців "
        "(наприклад, 'Ремонт душу на 3-му поверсі')",
    )

    target_room = models.ForeignKey(
        "Room",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="announcements",
        help_text="Оберіть кімнату, якщо це адресне попередження або повідомлення для конкретної кімнати",
    )

    target_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="targeted_announcements",
        help_text="Список конкретних студентів, якщо повідомлення призначене особисто для них",
    )

    title = models.CharField(max_length=255, help_text="Короткий заголовок оголошення")
    message = models.TextField(help_text="Повний текст оголошення")

    created_at = models.DateTimeField(auto_now_add=True, help_text="Час створення оголошення")
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Час, коли оголошення перестане бути актуальним і зникне зі стрічки мешканців, "
        "якщо null - до першого перегляду",
    )
    is_pinned = models.BooleanField(
        default=False, help_text="Якщо True, оголошення буде закріплене вгорі стрічки, незалежно від дати створення"
    )

    def clean(self):
        super().clean()
        if hasattr(self, "target_type") and self.target_type is not None:
            if self.target_type.type == "FLOOR" and not self.target_floor:
                raise ValidationError("Для оголошення на поверх необхідно обрати поверх.")

            if self.target_type.type == "ROOM" and not self.target_room:
                raise ValidationError("Для оголошення на кімнату необхідно обрати кімнату.")

    def __str__(self):
        return f"[{self.target_type.type}] {self.title}"


class AnnouncementRead(models.Model):
    announcement = models.ForeignKey(
        Announcement, on_delete=models.CASCADE, related_name="reads", help_text="Оголошення, яке було прочитане"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="read_announcements",
        help_text="Користувач, який переглянув це оголошення",
    )

    read_at = models.DateTimeField(
        auto_now_add=True, help_text="Точний час, коли користувач відкрив або позначив оголошення як прочитане"
    )

    class Meta:
        unique_together = ("announcement", "user")

    def __str__(self):
        return f"{self.user.email} прочитав '{self.announcement.title}'"
