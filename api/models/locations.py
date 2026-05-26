from django.db import models
from django.core.validators import MinValueValidator


class Dormitory(models.Model):
    name = models.CharField(max_length=255, help_text="Офіційна назва гуртожитку (наприклад, 'Гуртожиток №3')")
    location = models.CharField(
        max_length=500, null=True, blank=True, help_text="Фізична адреса або геолокація будівлі"
    )

    def __str__(self):
        return self.name


class Floor(models.Model):
    dormitory = models.ForeignKey(
        Dormitory, on_delete=models.CASCADE, related_name="floors", help_text="Гуртожиток, до якого належить цей поверх"
    )
    number = models.IntegerField(
        help_text="Номер поверху (наприклад, 1, 2, 3)", unique=True, validators=[MinValueValidator(1)]
    )
    map_file = models.FileField(
        upload_to="maps/",
        help_text="Файл інтерактивної карти поверху (у форматі SVG), на якому відмальовуються кімнати",
    )

    def __str__(self):
        return f"{self.dormitory.name} - Поверх {self.number}"


class RoomType(models.Model):
    type = models.CharField(
        max_length=50,
        unique=True,
        help_text="Категорія приміщення (наприклад, 'Житлова', 'Кухня', 'Душова', 'Пральня')",
    )

    def __str__(self):
        return self.type


class Room(models.Model):
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
        help_text="Якщо True, кімната повністю недоступна (наприклад, через капітальний ремонт, санітарний день тощо)",
    )
    svg_element_id = models.CharField(
        max_length=100,
        help_text="ID елемента (полігону/шляху) всередині SVG-карти поверху. "
        "Використовується фронтендом для підсвічування цієї кімнати при наведенні.",
    )

    def __str__(self):
        return f"{self.name} (Поверх {self.floor.number})"


class Resource(models.Model):
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="resources",
        help_text="Кімната або приміщення, де фізично розташований цей ресурс",
    )
    name = models.CharField(
        max_length=100,
        help_text="Назва конкретного ресурсу для бронювання "
        "(наприклад, 'Пральна машина №1', 'Душова кабінка №2', 'Піч ліва')",
    )
    max_person = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Скільки людей можуть одночасно забронювати або використовувати цей ресурс (найчастіше 1)",
    )
    is_blocked = models.BooleanField(
        default=False, help_text="Якщо True, ресурс недоступний для бронювання (наприклад, зламалася пральна машина)"
    )

    def __str__(self):
        return f"{self.name} ({self.room.name})"
