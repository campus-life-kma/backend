from django.db import models
from django.conf import settings


class Presence(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="presences")
    room = models.ForeignKey("Room", on_delete=models.CASCADE, related_name="presences")

    joined_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"{self.user.email} У {self.room.name}"


class BookingStatus(models.Model):
    status = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.status


class Booking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")
    resource = models.ForeignKey("Resource", on_delete=models.CASCADE, related_name="bookings")

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    status = models.ForeignKey(BookingStatus, on_delete=models.PROTECT, related_name="bookings")

    def __str__(self):
        return f"Бронювання: {self.resource.name} {self.user.email} ({self.start_time.strftime('%H:%M')})"
