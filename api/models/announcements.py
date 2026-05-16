from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings


class TargetType(models.Model):
    type = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.type


class Announcement(models.Model):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_announcements"
    )

    target_type = models.ForeignKey(TargetType, on_delete=models.PROTECT, related_name="announcements")

    target_floor = models.ForeignKey(
        "Floor", on_delete=models.CASCADE, null=True, blank=True, related_name="announcements"
    )

    target_room = models.ForeignKey(
        "Room", on_delete=models.CASCADE, null=True, blank=True, related_name="announcements"
    )

    target_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="targeted_announcements")

    title = models.CharField(max_length=255)
    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_pinned = models.BooleanField(default=False)

    def clean(self):
        super().clean()
        if hasattr(self, "target_type") and self.target_type is not None:
            if self.target_type.name == "Поверх" and not self.target_floor:
                raise ValidationError("Для типу Поверх необхідно обов'язково обрати поверх.")

            if self.target_type.name == "Кімната" and not self.target_room:
                raise ValidationError("Для типу Кімната необхідно обов'язково обрати кімнату.")

    def __str__(self):
        return f"[{self.target_type.name}] {self.title}"


class AnnouncementRead(models.Model):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name="reads")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="read_announcements")

    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("announcement", "user")

    def __str__(self):
        return f"{self.user.email} прочитав '{self.announcement.title}'"
