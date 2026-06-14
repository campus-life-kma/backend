import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


class Faculty(models.Model):
    """Модель факультету."""

    name = models.CharField(
        max_length=255, unique=True, help_text="Повна назва факультету (наприклад, Факультет інформатики)"
    )

    def __str__(self):
        return self.name


class Major(models.Model):
    """Модель спеціальності, що належить до конкретного факультету."""

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
    """Модель ролі користувача у системі (ADMIN, MODERATOR, RESIDENT)."""

    name = models.CharField(
        max_length=100, unique=True, help_text="Унікальна назва системної ролі (ADMIN, MODERATOR, RESIDENT)"
    )

    def __str__(self):
        return self.name


class User(AbstractUser):
    """Кастомна модель користувача Campus Life, яка використовує email як головний ідентифікатор."""

    class EducationLevel(models.TextChoices):
        BACHELOR = "BACHELOR", "Бакалавр"
        MASTER = "MASTER", "Магістр"
        PHD = "PHD", "Аспірант"

    class Position(models.TextChoices):
        STUDENT = "STUDENT", "Студент"
        TEACHER = "TEACHER", "Викладач"
        EMPLOYEE = "EMPLOYEE", "Працівник"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, help_text="Унікальний ідентифікатор користувача (UUID)"
    )

    username = None  # Вимикаємо стандартне поле username, оскільки використовуємо email
    email = models.EmailField(unique=True, help_text="Корпоративна електронна пошта (наприклад, @ukma.edu.ua)")

    full_name = models.CharField(max_length=500, null=True, blank=True, help_text="Повне ім'я мешканця")

    position = models.CharField(
        max_length=20,
        choices=Position.choices,
        default=Position.STUDENT,
        help_text="Позиція у ВНЗ (Студент, Викладач, Працівник)",
    )

    education_level = models.CharField(
        max_length=20,
        choices=EducationLevel.choices,
        null=True,
        blank=True,
        help_text="Рівень навчання користувача: бакалаврат, магістратура або аспірантура",
    )
    year = models.SmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        help_text="Курс або рік навчання (від 1 до 4; для магістратури доступні 1-2)",
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
        help_text="Системна роль, яка визначає рівень доступу",
    )
    major = models.ForeignKey(
        Major,
        related_name="users",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Спеціальність, на якій навчається мешканець",
    )
    faculty = models.ForeignKey(
        Faculty,
        related_name="direct_users",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Факультет, до якого належить користувач",
    )

    status = models.CharField(max_length=100, blank=True, help_text="Короткий статус або настрій")
    bio = models.TextField(blank=True, help_text="Детальна інформація про себе")
    photo = models.ImageField(upload_to="avatars/", null=True, blank=True, help_text="Файл аватарки профілю")

    is_activated = models.BooleanField(
        default=False,
        help_text="Прапорець активації після першого логіну",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    @property
    def is_admin(self) -> bool:
        """Перевіряє, чи має користувач роль ADMIN."""
        return bool(self.role and self.role.name == "ADMIN")

    @property
    def is_moderator(self) -> bool:
        """Перевіряє, чи має користувач роль MODERATOR."""
        return bool(self.role and self.role.name == "MODERATOR")

    def __str__(self):
        if self.full_name:
            return f"{self.email} ({self.full_name})"
        return self.email
