import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


class Faculty(models.Model):
    name = models.CharField(
        max_length=255, unique=True, help_text="Повна назва факультету (наприклад, Факультет інформатики)"
    )

    def __str__(self):
        return self.name


class Major(models.Model):
    faculty = models.ForeignKey(
        Faculty,
        related_name="majors",
        on_delete=models.CASCADE,
        help_text="Факультет, до якого належить ця спеціальність",
    )
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Тільки назва спеціальності (наприклад, Інженерія програмного забезпечення)",
    )

    def __str__(self):
        return f"{self.name} ({self.faculty.name})"


class Role(models.Model):
    name = models.CharField(
        max_length=100, unique=True, help_text="Унікальна назва системної ролі (ADMIN, MODERATOR, RESIDENT)"
    )

    def __str__(self):
        return self.name


class User(AbstractUser):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, help_text="Унікальний ідентифікатор користувача (UUID)"
    )

    username = None
    email = models.EmailField(unique=True, help_text="Корпоративна електронна пошта (наприклад, @ukma.edu.ua)")

    surname = models.CharField(max_length=100, null=True, blank=True, help_text="Прізвище мешканця")
    name = models.CharField(max_length=100, null=True, blank=True, help_text="Ім'я мешканця")
    middle_name = models.CharField(max_length=100, null=True, blank=True, help_text="По батькові")
    year = models.SmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        help_text="Курс навчання (від 1 до 4)",
    )

    room = models.ForeignKey(
        "Room",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Кімната в гуртожитку, за якою закріплений студент",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Системна роль, яка визначає рівень доступу до функцій платформи",
    )
    major = models.ForeignKey(
        Major,
        related_name="users",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Спеціальність, на якій навчається мешканець",
    )

    status = models.CharField(
        max_length=100, blank=True, help_text="Короткий статус або настрій (відображається в публічному профілі)"
    )
    bio = models.TextField(blank=True, help_text="Детальна інформація про себе: інтереси, соц мережі, хобі тощо")
    photo = models.ImageField(upload_to="avatars/", null=True, blank=True, help_text="Файл аватарки профілю")

    is_activated = models.BooleanField(
        default=False,
        help_text="Прапорець активації (стає True після першого логіну та заповнення обов'язкових полів профілю)",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    @property
    def is_admin(self) -> bool:
        return self.role and self.role.name == "ADMIN"

    @property
    def is_moderator(self) -> bool:
        return self.role and self.role.name == "MODERATOR"

    def __str__(self):
        if self.name and self.surname:
            return f"{self.email} ({self.name} {self.surname})"
        return self.email
