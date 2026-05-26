from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from api.models import Room, Faculty, Major, Role, User


class Command(BaseCommand):
    help = "Наповнює базу тестовими даними (користувачами) для локальної розробки"

    def handle(self, *args, **kwargs):
        self.stdout.write("Починаємо генерацію тестових даних...")

        try:
            room_41_2 = Room.objects.get(name="41/2")
            room_41_1 = Room.objects.get(name="41/1")
            room_admin = Room.objects.get(name="Адміністрація")

            resident_role = Role.objects.get(name="RESIDENT")
            moderator_role = Role.objects.get(name="MODERATOR")
            admin_role = Role.objects.get(name="ADMIN")
        except Room.DoesNotExist, Role.DoesNotExist:
            self.stderr.write("Помилка: Кімнати або Ролі не знайдені. Спочатку виконайте міграції (migrate).")
            return

        faculty_t, _ = Faculty.objects.get_or_create(name="Тестовий факультет")
        major_t, _ = Major.objects.get_or_create(faculty=faculty_t, name="Тестова спеціальність")

        unusable_password = make_password(None)
        admin_password = make_password("Qwerty1234!")

        test_emails = [
            "d.bezukh@ukma.edu.ua",
            "b.zmeul@ukma.edu.ua",
            "d.lapko@ukma.edu.ua",
            "user1@ukma.edu.ua",
            "user2@ukma.edu.ua",
            "user3@ukma.edu.ua",
            "moderator@ukma.edu.ua",
            "admin@ukma.edu.ua",
        ]
        deleted_count, _ = User.objects.filter(email__in=test_emails).delete()
        if deleted_count > 0:
            self.stdout.write(f"Очищено {deleted_count} старих тестових користувачів.")

        User.objects.bulk_create(
            [
                User(
                    email="d.bezukh@ukma.edu.ua",
                    password=unusable_password,
                    role=resident_role,
                    room=room_41_2,
                    is_activated=False,
                ),
                User(
                    email="b.zmeul@ukma.edu.ua",
                    password=unusable_password,
                    role=resident_role,
                    room=room_41_2,
                    is_activated=False,
                ),
                User(
                    email="d.lapko@ukma.edu.ua",
                    password=unusable_password,
                    role=resident_role,
                    room=room_41_2,
                    is_activated=False,
                ),
            ]
        )

        User.objects.bulk_create(
            [
                User(
                    email="user1@ukma.edu.ua",
                    password=unusable_password,
                    role=resident_role,
                    room=room_41_1,
                    is_activated=True,
                    full_name="Коваленко Дмитро",
                    year=4,
                    major=major_t,
                    status="Вчуся",
                    bio="Працюю над проєктами та дедлайнами.",
                ),
                User(
                    email="user2@ukma.edu.ua",
                    password=unusable_password,
                    role=resident_role,
                    room=room_41_1,
                    is_activated=True,
                    full_name="Шевченко Іван",
                    year=3,
                    major=major_t,
                    bio="Збираю ресурси на лабораторні роботи.",
                ),
                User(
                    email="user3@ukma.edu.ua",
                    password=unusable_password,
                    role=resident_role,
                    room=room_41_1,
                    is_activated=True,
                    full_name="Бойко Олексій",
                    year=2,
                    major=major_t,
                    status="На кухні",
                ),
            ]
        )

        User.objects.create(
            email="moderator@ukma.edu.ua",
            password=unusable_password,
            role=moderator_role,
            room=room_admin,
            is_activated=True,
            full_name="Староста Поверху",
        )

        User.objects.create(
            email="admin@ukma.edu.ua",
            password=admin_password,
            role=admin_role,
            room=room_admin,
            is_activated=True,
            is_staff=True,
            is_superuser=True,
            full_name="Головний Адміністратор",
            status="Бог сервера",
            bio="Маю доступ до всіх таблиць бази даних.",
        )

        self.stdout.write(self.style.SUCCESS("Успішно згенеровано тестових користувачів!"))
