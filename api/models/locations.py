from django.db import models
from django.core.validators import MinValueValidator


class Dormitory(models.Model):
    """Модель гуртожитку."""

    name = models.CharField(max_length=255, help_text="Офіційна назва гуртожитку (наприклад, 'Гуртожиток №3')")
    location = models.CharField(
        max_length=500, null=True, blank=True, help_text="Фізична адреса або геолокація будівлі"
    )

    def __str__(self):
        return self.name


class Floor(models.Model):
    """Модель поверху гуртожитку, що містить файл карти та попередження."""

    dormitory = models.ForeignKey(
        Dormitory, on_delete=models.CASCADE, related_name="floors", help_text="Гуртожиток, до якого належить цей поверх"
    )
    number = models.IntegerField(help_text="Номер поверху (наприклад, 1, 2, 3)", validators=[MinValueValidator(1)])
    map_file = models.FileField(
        upload_to="maps/",
        help_text="Файл інтерактивної карти поверху (у форматі SVG), на якому відмальовуються кімнати",
    )
    notice = models.TextField(
        blank=True,
        default="",
        help_text="Коротке попередження для відображення на мапі цього поверху, якщо воно потрібне",
    )

    class Meta:
        constraints = [models.UniqueConstraint(fields=["dormitory", "number"], name="unique_floor_per_dormitory")]

    def __str__(self):
        return f"{self.dormitory.name} - Поверх {self.number}"


class RoomType(models.Model):
    """Словникова модель для типів приміщень (LIVING, KITCHEN, LAUNDRY тощо)."""

    type = models.CharField(
        max_length=50,
        unique=True,
        help_text="Категорія приміщення (наприклад, 'Житлова', 'Кухня', 'Душова', 'Пральня')",
    )

    def __str__(self):
        return self.type


class Room(models.Model):
    """Модель конкретної кімнати або зони на поверсі."""

    floor = models.ForeignKey(
        Floor, on_delete=models.CASCADE, related_name="rooms", help_text="Поверх, на якому знаходиться кімната"
    )
    name = models.CharField(
        max_length=100, help_text="Номер або назва кімнати (наприклад, '314', 'Кухня лівого крила')"
    )

    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.PROTECT,
        related_name="rooms",
        help_text="Тип кімнати, який визначає її призначення та правила використання",
    )
    max_person = models.SmallIntegerField(
        validators=[MinValueValidator(0)],
        help_text="Максимальна місткість. Для житлових — кількість ліжок, для спільних — ліміт людей.",
    )
    is_blocked = models.BooleanField(
        default=False,
        help_text="Якщо True, кімната повністю недоступна (наприклад, через ремонт)",
    )
    svg_element_id = models.CharField(
        max_length=100,
        help_text="ID елемента всередині SVG-карти поверху для підсвічування на фронтенді",
    )

    def __str__(self):
        return f"{self.name} (Поверх {self.floor.number})"


class ResourceType(models.Model):
    """Словникова модель для типів ресурсів (WASHING_MACHINE, COOKTOP тощо) та їх іконок."""

    type = models.CharField(max_length=50, unique=True, help_text="Тип ресурсу, наприклад пралка")
    icon_file = models.FileField(
        upload_to="resource-icons/",
        help_text="Файл типу ресурсу (у форматі SVG), який буде відмальовуватися на фронтенді",
    )

    def __str__(self):
        return f"{self.type}"


class Resource(models.Model):
    """Модель ресурсу для бронювання, розташованого у певній кімнаті."""

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="resources",
        help_text="Кімната або приміщення, де фізично розташований цей ресурс",
    )
    resource_type = models.ForeignKey(
        ResourceType, on_delete=models.PROTECT, related_name="resources", help_text="Тип ресурсу"
    )
    name = models.CharField(
        max_length=100,
        help_text="Назва конкретного ресурсу для бронювання (наприклад, 'Пральна машина №1')",
    )
    max_person = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Скільки людей можуть одночасно забронювати або використовувати цей ресурс (найчастіше 1)",
    )
    is_blocked = models.BooleanField(default=False, help_text="Якщо True, ресурс недоступний для бронювання")

    def __str__(self):
        return f"{self.name} ({self.room.name})"
