from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, CheckConstraint
from django.core.exceptions import ValidationError
from django.conf import settings


class SocialEvent(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_events")
    room = models.ForeignKey("Room", on_delete=models.CASCADE, null=True, blank=True, related_name="events")
    floor = models.ForeignKey("Floor", on_delete=models.CASCADE, null=True, blank=True, related_name="events")

    custom_location = models.CharField(max_length=255, null=True, blank=True)

    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    max_person = models.IntegerField(validators=[MinValueValidator(0)])

    is_faculty_only = models.BooleanField(default=False)
    is_major_only = models.BooleanField(default=False)

    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="participating_events", blank=True)

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
    status = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.status


class SocialSharingRequest(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sharing_requests")
    title = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)

    status = models.ForeignKey(SocialSharingStatus, on_delete=models.PROTECT, related_name="requests")

    def __str__(self):
        return f"[{self.status.status}] {self.title} (Автор: {self.creator.email})"
