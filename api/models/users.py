import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


class Faculty(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Major(models.Model):
    faculty = models.ForeignKey(Faculty, related_name="majors", on_delete=models.CASCADE)
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.name} ({self.faculty.name})"


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    username = None
    email = models.EmailField(unique=True)

    surname = models.CharField(max_length=100, null=True, blank=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    year = models.SmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(4)])

    room = models.ForeignKey("Room", on_delete=models.SET_NULL, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, null=True, blank=True)
    major = models.ForeignKey(Major, related_name="users", on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="avatars/", null=True, blank=True)

    is_activated = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        if self.name and self.surname:
            return f"{self.email} ({self.name} {self.surname})"
        return self.email
