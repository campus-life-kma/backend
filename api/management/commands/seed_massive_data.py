import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from api.models import (
    Room,
    Major,
    Role,
    User,
    Resource,
    SocialEvent,
    SocialSharingRequest,
    SocialSharingStatus,
    Booking,
    BookingStatus,
)


class Command(BaseCommand):
    """Манагемент-команда для генерації великої кількості тестових даних для симуляції реального навантаження."""

    help = "Наповнює базу великою кількістю тестових даних для симуляції реального навантаження"

    def handle(self, *args, **kwargs):
        """Головна точка входу. Оркеструє весь процес генерації даних.

        Очищає старі дані, створює 200 користувачів, 50 подій,
        100 запитів на шеринг та 500 бронювань.

        Args:
            *args: Позиційні аргументи Django.
            **kwargs: Названі аргументи Django.
        """
        self.stdout.write("Починаємо генерацію МАСИВНИХ тестових даних...")

        try:
            resident_role = Role.objects.get(name="RESIDENT")
            active_sharing = SocialSharingStatus.objects.get(status="ACTIVE")
            completed_sharing = SocialSharingStatus.objects.get(status="COMPLETED")
            active_booking = BookingStatus.objects.get(status="ACTIVE")
            cancelled_booking = BookingStatus.objects.get(status="CANCELLED")
        except (Role.DoesNotExist, SocialSharingStatus.DoesNotExist, BookingStatus.DoesNotExist) as e:
            self.stderr.write(f"Помилка: Базові статуси не знайдені ({e}). Спочатку виконайте міграції (migrate).")
            return

        living_rooms = list(Room.objects.filter(room_type__type="LIVING").exclude(floor__number=1))
        if not living_rooms:
            self.stderr.write("Помилка: Немає житлових кімнат. Перевірте, чи існують кімнати в базі.")
            return

        majors = list(Major.objects.all())
        if not majors:
            self.stderr.write("Помилка: Немає спеціальностей в базі.")
            return

        # Збираємо всі незаблоковані ресурси — це потрібно для генерації бронювань
        resources = list(Resource.objects.all())

        self._clear_old_data()

        available_slots = self._get_available_slots()

        users = self._create_massive_users(resident_role, available_slots, majors)

        self._generate_sharing_requests(users, active_sharing, completed_sharing)
        self._generate_social_events(users, active_sharing, living_rooms)
        self._generate_bookings(users, resources, active_booking, cancelled_booking)

        self.stdout.write(self.style.SUCCESS("Успішно згенеровано МАСИВНІ тестові дані!"))

    def _clear_old_data(self):
        """Видаляє старі масивні дані (події, шеринг, бронювання та масивних користувачів)."""
        self.stdout.write("Очищення старих даних (івенти, шеринг, бронювання)...")
        SocialEvent.objects.all().delete()
        SocialSharingRequest.objects.all().delete()
        Booking.objects.all().delete()
        User.objects.filter(email__startswith="massive_user_").delete()

    def _get_available_slots(self):
        """Повертає список вільних місць у житлових кімнатах (крім 1-го поверху).

        Знаходить усі житлові кімнати, підраховує зайнятих мешканців і додає
        до списку посилання для кожного вільного місця.

        Returns:
            list[Room]: Перемішаний список кімнат зі слотами для нових користувачів.
        """
        from django.db.models import Count

        rooms_with_counts = (
            Room.objects.filter(room_type__type="LIVING")
            .exclude(floor__number=1)
            .annotate(current_residents=Count("user"))
        )

        available_slots = []
        for r in rooms_with_counts:
            if r.is_blocked:
                continue
            # Кількість вільних місць = максимальна місткість мінус поточна зайнятість
            free_slots = r.max_person - r.current_residents
            for _ in range(free_slots):
                # Додаємо кімнату по free_slots разів, щоб кожен майбутній юзер отримав окремий слот
                available_slots.append(r)

        random.shuffle(available_slots)
        return available_slots

    def _create_massive_users(self, resident_role, available_slots, majors):
        """Створює до 200 тестових користувачів (або менше, якщо вільних місць недостатньо).

        Args:
            resident_role: Об'єкт ролі RESIDENT.
            available_slots: Список вільних місць у кімнатах.
            majors: Список спеціальностей для випадкового призначення студентам.

        Returns:
            list[User]: Створені користувачі (завантажені з БД).
        """
        unusable_password = make_password("password123")
        num_users = min(200, len(available_slots))
        self.stdout.write(f"Створення {num_users} користувачів...")

        first_names = [
            "Олександр",
            "Максим",
            "Іван",
            "Андрій",
            "Дмитро",
            "Артем",
            "Владислав",
            "Анастасія",
            "Дарина",
            "Марія",
            "Катерина",
            "Софія",
            "Вікторія",
            "Анна",
            "Поліна",
        ]
        last_names = [
            "Бойко",
            "Коваленко",
            "Шевченко",
            "Мельник",
            "Ткаченко",
            "Кравченко",
            "Лисенко",
            "Петренко",
            "Олійник",
            "Савченко",
            "Григоренко",
            "Романенко",
        ]

        users_to_create = []
        for i in range(1, num_users + 1):
            # Розподіл позицій: 80% — студенти, 15% — викладачі, 5% — співробітники
            pos = random.choices(
                [User.Position.STUDENT, User.Position.TEACHER, User.Position.EMPLOYEE], weights=[80, 15, 5]
            )[0]

            full_name = f"{random.choice(first_names)} {random.choice(last_names)}"

            user_data = dict(
                email=f"massive_user_{i}@ukma.edu.ua",
                password=unusable_password,
                role=resident_role,
                room=available_slots[i - 1],
                is_activated=True,
                full_name=full_name,
                status=random.choice(["Вчуся", "Сплю", "На парах", "", "Пишу код"]),
                bio="Тестовий акаунт для масивних даних.",
                position=pos,
            )

            if pos == User.Position.STUDENT:
                # Для студентів додаємо рівень освіти, курс і спеціальність
                user_data["education_level"] = random.choices(["BACHELOR", "MASTER", "PHD"], weights=[70, 20, 10])[0]
                user_data["year"] = (
                    random.randint(1, 4) if user_data["education_level"] != "MASTER" else random.randint(1, 2)
                )
                user_data["major"] = random.choice(majors)
            elif pos == User.Position.TEACHER:
                # Викладачі не мають major, тільки faculty
                user_data["faculty"] = random.choice(majors).faculty

            users_to_create.append(User(**user_data))

        User.objects.bulk_create(users_to_create)
        return list(User.objects.filter(email__startswith="massive_user_"))

    def _generate_sharing_requests(self, users, active_sharing, completed_sharing):
        """Генерує 100 запитів на шеринг з випадковими статусами.

        Args:
            users: Список доступних користувачів.
            active_sharing: Статус ACTIVE.
            completed_sharing: Статус COMPLETED.
        """
        self.stdout.write("Генерація 100 запитів на шеринг...")
        sharing_requests = []
        sharing_titles = [
            "Позичте праску",
            "Потрібна сіль",
            "Хто має зарядку Type-C?",
            "Шукаю HDMI кабель",
            "Потрібен штопор",
            "Хто може позичити пилосос?",
            "Шукаю зошит в клітинку",
            "Потрібен скотч",
        ]
        for i in range(100):
            sharing_requests.append(
                SocialSharingRequest(
                    creator=random.choice(users),
                    title=f"{random.choice(sharing_titles)} #{i}",
                    status=random.choice([active_sharing, completed_sharing]),
                )
            )
        SocialSharingRequest.objects.bulk_create(sharing_requests)

    def _generate_social_events(self, users, active_sharing, living_rooms):
        """Генерує 50 соціальних подій з випадковими назвами та часом.

        Args:
            users: Список доступних користувачів.
            active_sharing: Статус ACTIVE для подій.
            living_rooms: Список житлових кімнат для вибору локації подій.
        """
        self.stdout.write("Генерація 50 соціальних подій...")
        now = timezone.now()
        event_titles = [
            "Вечір настілок",
            "Кінопоказ",
            "Спільне приготування їжі",
            "Хакатон",
            "Ранкова пробіжка",
            "Турнір з FIFA",
            "Обговорення диплому",
        ]
        for i in range(50):
            start = now + timedelta(days=random.randint(-2, 7), hours=random.randint(1, 12))
            max_p = random.randint(0, 15)
            event = SocialEvent(
                creator=random.choice(users),
                status=active_sharing,
                title=f"{random.choice(event_titles)} #{i}",
                description="Опис тестової події для масивних даних.",
                start_time=start,
                end_time=start + timedelta(hours=random.randint(1, 4)),
                max_person=max_p,
                room=random.choice(living_rooms),
            )
            event.save()
            # Обмежуємо max_p=0 — це означає "без обмежень", використовуємо до 15 як fallback
            limit = max_p if max_p > 0 else 15
            num_participants = random.randint(1, limit)
            participants = random.sample(users, num_participants)
            event.participants.add(*participants)

    def _generate_bookings(self, users, resources, active_booking, cancelled_booking):
        """Генерує 500 бронювань з випадковими часом та статусами.

        Бронювання можуть перетинатися або мати статус CANCELLED.
        Якщо ресурсів немає, генерація пропускається.

        Args:
            users: Список доступних користувачів.
            resources: Список ресурсів для бронювання.
            active_booking: Статус ACTIVE.
            cancelled_booking: Статус CANCELLED.
        """
        self.stdout.write("Генерація 500 бронювань...")
        if resources:
            now = timezone.now()
            bookings_to_create = []
            for i in range(500):
                resource = random.choice(resources)
                # Час початку випадково у минулому/майбутньому для реалістичного розкладу
                start = now + timedelta(days=random.randint(-7, 7), hours=random.randint(-12, 12))
                start = start.replace(minute=random.choice([0, 30]), second=0, microsecond=0)
                end = start + timedelta(hours=random.choice([1, 2]))
                bookings_to_create.append(
                    Booking(
                        user=random.choice(users),
                        resource=resource,
                        start_time=start,
                        end_time=end,
                        # Бронювання можуть перетинатися — це дозволено для симуляції реальних даних
                        status=random.choice([active_booking, cancelled_booking]),
                    )
                )

            Booking.objects.bulk_create(bookings_to_create)
