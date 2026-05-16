from django.db import models
from django.core.validators import MinValueValidator


class Dormitory(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return self.name


class Floor(models.Model):
    dormitory = models.ForeignKey(Dormitory, on_delete=models.CASCADE, related_name="floors")
    number = models.IntegerField()
    map_file = models.FileField(upload_to="maps/")

    def __str__(self):
        return f"{self.dormitory.name} - Поверх {self.number}"


class RoomType(models.Model):
    type = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.type


class Room(models.Model):
    floor = models.ForeignKey(Floor, on_delete=models.CASCADE, related_name="rooms")
    name = models.CharField(max_length=100)

    room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT, related_name="rooms")
    max_person = models.SmallIntegerField(validators=[MinValueValidator(0)])
    is_blocked = models.BooleanField(default=False)
    svg_element_id = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} (Поверх {self.floor.number})"


class Resource(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="resources")
    name = models.CharField(max_length=100)
    max_person = models.IntegerField(validators=[MinValueValidator(1)])
    is_blocked = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.room.name})"
