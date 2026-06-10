import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from api.models import (
    Room,
    Faculty,
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
    help = "Наповнює базу великою кількістю тестових даних для симуляції реального навантаження"

    def handle(self, *args, **kwargs):
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

        living_rooms = list(Room.objects.filter(room_type__type="LIVING"))
        if not living_rooms:
            self.stderr.write("Помилка: Немає житлових кімнат. Перевірте, чи існують кімнати в базі.")
            return

        majors = list(Major.objects.all())
        if not majors:
            self.stderr.write("Помилка: Немає спеціальностей в базі.")
            return

        resources = list(Resource.objects.all())

        unusable_password = make_password("password123")

        self.stdout.write("Очищення старих даних (івенти, шеринг, бронювання)...")
        SocialEvent.objects.all().delete()
        SocialSharingRequest.objects.all().delete()
        Booking.objects.all().delete()

        # Видалення старих масивних користувачів
        User.objects.filter(email__startswith="massive_user_").delete()

        self.stdout.write("Створення 200 користувачів...")
        
        first_names = ["Олександр", "Максим", "Іван", "Андрій", "Дмитро", "Артем", "Владислав", "Анастасія", "Дарина", "Марія", "Катерина", "Софія", "Вікторія", "Анна", "Поліна"]
        last_names = ["Бойко", "Коваленко", "Шевченко", "Мельник", "Ткаченко", "Кравченко", "Лисенко", "Петренко", "Олійник", "Савченко", "Григоренко", "Романенко"]

        users_to_create = []
        for i in range(1, 201):
            pos = random.choices(
                [User.Position.STUDENT, User.Position.TEACHER, User.Position.EMPLOYEE], 
                weights=[80, 15, 5]
            )[0]
            
            full_name = f"{random.choice(first_names)} {random.choice(last_names)}"
            
            user_data = dict(
                email=f"massive_user_{i}@ukma.edu.ua",
                password=unusable_password,
                role=resident_role,
                room=random.choice(living_rooms),
                is_activated=True,
                full_name=full_name,
                status=random.choice(["Вчуся", "Сплю", "На парах", "", "Пишу код"]),
                bio="Тестовий акаунт для масивних даних.",
                position=pos,
            )
            
            if pos == User.Position.STUDENT:
                user_data["education_level"] = random.choices(['BACHELOR', 'MASTER', 'PHD'], weights=[70, 20, 10])[0]
                user_data["year"] = random.randint(1, 4) if user_data["education_level"] != 'MASTER' else random.randint(1, 2)
                user_data["major"] = random.choice(majors)
            elif pos == User.Position.TEACHER:
                user_data["faculty"] = random.choice(majors).faculty
            
            users_to_create.append(User(**user_data))

        User.objects.bulk_create(users_to_create)
        users = list(User.objects.filter(email__startswith="massive_user_"))

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
        events = []
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
            events.append(event)
            # Додаємо учасників, не перевищуючи ліміт
            limit = max_p if max_p > 0 else 15
            num_participants = random.randint(1, limit)
            participants = random.sample(users, num_participants)
            event.participants.add(*participants)

        self.stdout.write("Генерація 500 бронювань...")
        if resources:
            bookings_to_create = []
            for i in range(500):
                resource = random.choice(resources)
                # Рандомний час в межах тижня (минулого чи майбутнього)
                start = now + timedelta(days=random.randint(-7, 7), hours=random.randint(-12, 12))
                # Округляємо до 30 хвилин для реалістичності
                start = start.replace(minute=random.choice([0, 30]), second=0, microsecond=0)
                end = start + timedelta(hours=random.choice([1, 2]))
                bookings_to_create.append(
                    Booking(
                        user=random.choice(users),
                        resource=resource,
                        start_time=start,
                        end_time=end,
                        status=random.choice([active_booking, cancelled_booking]),
                    )
                )
            # Будуть колізії, але bulk_create ігнорує бізнес-логіку з сервісів (що ок для seed'а, якщо не на рівні БД)
            # Щоб уникнути помилок на рівні БД (якщо є constraints), просто створюємо
            Booking.objects.bulk_create(bookings_to_create)

        self.stdout.write(self.style.SUCCESS("Успішно згенеровано МАСИВНІ тестові дані!"))
