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
    TargetType,
    Announcement,
)


class Command(BaseCommand):
    help = "Наповнює базу багатими тестовими даними для локальної розробки та демо"

    def handle(self, *args, **kwargs):
        self.stdout.write("Починаємо генерацію тестових даних...")

        try:
            room_41_2 = Room.objects.get(name="41/2")
            room_41_1 = Room.objects.get(name="41/1")
            room_42_1 = Room.objects.get(name="42/1")
            room_42_2 = Room.objects.get(name="42/2")

            room_51_1 = Room.objects.get(name="51/1")
            room_52_2 = Room.objects.get(name="52/2")
            kitchen_5 = Room.objects.get(name="Кухня 53/1")

            laundry = Room.objects.get(name="Пральня")
            room_admin = Room.objects.get(name="Адміністрація")

            washing_machine_1 = Resource.objects.get(room=laundry, name="Пралка 1")
            washing_machine_2 = Resource.objects.get(room=laundry, name="Пралка 2")
            cooktop_1 = Resource.objects.get(room=kitchen_5, name="Варильна поверхня 1")

            resident_role = Role.objects.get(name="RESIDENT")
            moderator_role = Role.objects.get(name="MODERATOR")
            admin_role = Role.objects.get(name="ADMIN")

            active_sharing = SocialSharingStatus.objects.get(status="ACTIVE")
            completed_sharing = SocialSharingStatus.objects.get(status="COMPLETED")
            active_booking = BookingStatus.objects.get(status="ACTIVE")
        except (Room.DoesNotExist, Role.DoesNotExist, Resource.DoesNotExist) as e:
            self.stderr.write(f"Помилка: Базові дані не знайдені ({e}). Спочатку виконайте міграції (migrate).")
            return

        fi = Faculty.objects.get(name="Факультет Інформатики")
        se_major = Major.objects.get(faculty=fi, name="Інженерія програмного забезпечення")
        cs_major = Major.objects.get(faculty=fi, name="Комп'ютерні науки")

        fsen = Faculty.objects.get(name="Факультет економічних наук")
        marketing_major = Major.objects.get(faculty=fsen, name="Маркетинг")

        fsocial = Faculty.objects.get(name="Факультет соціальних наук та соціальних технологій")
        soc_major = Major.objects.get(faculty=fsocial, name="Соціологія")

        unusable_password = make_password(None)
        admin_password = make_password("Qwerty1234!")

        test_emails = [
            "d.bezukh@ukma.edu.ua",
            "b.zmeul@ukma.edu.ua",
            "d.lapko@ukma.edu.ua",
            "user1@ukma.edu.ua",
            "user2@ukma.edu.ua",
            "user3@ukma.edu.ua",
            "user4@ukma.edu.ua",
            "user5@ukma.edu.ua",
            "user6@ukma.edu.ua",
            "moderator@ukma.edu.ua",
            "admin@ukma.edu.ua",
            "teacher@ukma.edu.ua",
        ]

        SocialEvent.objects.all().delete()
        SocialSharingRequest.objects.all().delete()
        Booking.objects.all().delete()

        deleted_count, _ = User.objects.filter(email__in=test_emails).delete()
        User.objects.filter(email__startswith="moderator").delete()
        User.objects.filter(
            email__in=["watchman@ukma.edu.ua", "electrician@ukma.edu.ua", "plumber@ukma.edu.ua"]
        ).delete()

        self.stdout.write("Створення користувачів на 4 та 5 поверхах...")

        User.objects.bulk_create(
            [
                User(
                    email="d.bezukh@ukma.edu.ua",
                    password=unusable_password,
                    role=resident_role,
                    room=room_41_2,
                    is_activated=False,
                    position=User.Position.STUDENT,
                    education_level=User.EducationLevel.BACHELOR,
                ),
                User(
                    email="b.zmeul@ukma.edu.ua",
                    password=unusable_password,
                    role=resident_role,
                    room=room_41_2,
                    is_activated=False,
                    position=User.Position.STUDENT,
                    education_level=User.EducationLevel.BACHELOR,
                ),
                User(
                    email="d.lapko@ukma.edu.ua",
                    password=unusable_password,
                    role=resident_role,
                    room=room_41_2,
                    is_activated=False,
                    position=User.Position.STUDENT,
                    education_level=User.EducationLevel.BACHELOR,
                ),
            ]
        )

        u1 = User.objects.create(
            email="user1@ukma.edu.ua",
            password=unusable_password,
            role=resident_role,
            room=room_41_1,
            is_activated=True,
            full_name="Коваленко Дмитро",
            position=User.Position.STUDENT,
            education_level=User.EducationLevel.BACHELOR,
            year=4,
            major=se_major,
            status="Пишу диплом",
            bio="Люблю Python та Django. Завжди радий допомогти з кодом.",
        )
        u2 = User.objects.create(
            email="user2@ukma.edu.ua",
            password=unusable_password,
            role=resident_role,
            room=room_41_1,
            is_activated=True,
            full_name="Шевченко Іван",
            position=User.Position.STUDENT,
            education_level=User.EducationLevel.BACHELOR,
            year=3,
            major=cs_major,
            status="Вчу англійську",
            bio="Граю на гітарі, збираю кубик Рубіка.",
        )
        u3 = User.objects.create(
            email="user3@ukma.edu.ua",
            password=unusable_password,
            role=resident_role,
            room=room_42_1,
            is_activated=True,
            full_name="Бойко Олексій",
            position=User.Position.STUDENT,
            education_level=User.EducationLevel.BACHELOR,
            year=2,
            major=marketing_major,
            status="Шукаю стажування",
            bio="Маркетинг - це любов.",
        )
        u4 = User.objects.create(
            email="user4@ukma.edu.ua",
            password=unusable_password,
            role=resident_role,
            room=room_42_2,
            is_activated=True,
            full_name="Мельник Анна",
            position=User.Position.STUDENT,
            education_level=User.EducationLevel.BACHELOR,
            year=1,
            major=soc_major,
            status="Вчуся",
            bio="Першокурсниця. Обожнюю настільні ігри.",
        )

        u5 = User.objects.create(
            email="user5@ukma.edu.ua",
            password=unusable_password,
            role=resident_role,
            room=room_51_1,
            is_activated=True,
            full_name="Ткаченко Олена",
            position=User.Position.STUDENT,
            education_level=User.EducationLevel.BACHELOR,
            year=3,
            major=se_major,
            status="На кухні",
            bio="Люблю готувати та ділитися рецептами.",
        )
        u6 = User.objects.create(
            email="user6@ukma.edu.ua",
            password=unusable_password,
            role=resident_role,
            room=room_52_2,
            is_activated=True,
            full_name="Григоренко Максим",
            position=User.Position.STUDENT,
            education_level=User.EducationLevel.BACHELOR,
            year=4,
            major=cs_major,
            status="Сплю",
            bio="Не турбувати до 12:00.",
        )

        User.objects.create(
            email="moderator@ukma.edu.ua",
            password=unusable_password,
            role=moderator_role,
            room=room_41_1,
            is_activated=True,
            full_name="Староста 4-го Поверху",
            major=se_major,
            position=User.Position.STUDENT,
            education_level=User.EducationLevel.MASTER,
            year=1,
            status="Чергую",
            bio="Староста 4-го поверху. Звертайтеся з будь-якими питаннями щодо порядку.",
        )
        admin = User.objects.create(
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
            position=User.Position.EMPLOYEE,
        )
        User.objects.create(
            email="teacher@ukma.edu.ua",
            password=unusable_password,
            role=resident_role,
            room=room_42_2,
            is_activated=True,
            full_name="Петров Петро Петрович",
            position=User.Position.TEACHER,
            faculty=fi,
            status="Перевіряю роботи",
            bio="Викладач кафедри інформатики НаУКМА. Проживаю тимчасово в гуртожитку.",
        )

        room_doorman = Room.objects.get(name="Кімната швейцара")
        room_watch = Room.objects.get(name="Вахта")

        User.objects.create(
            email="watchman@ukma.edu.ua",
            password=unusable_password,
            role=resident_role,
            room=room_watch,
            is_activated=True,
            full_name="Ковальчук Петро (Вахтер)",
            position=User.Position.EMPLOYEE,
            bio="Черговий вахтер гуртожитку. Завжди на варті порядку.",
        )
        User.objects.create(
            email="electrician@ukma.edu.ua",
            password=unusable_password,
            role=resident_role,
            room=room_doorman,
            is_activated=True,
            full_name="Грицюк Ігор (Електрик)",
            position=User.Position.EMPLOYEE,
            bio="Черговий електрик гуртожитку. Звертайтеся щодо проблем з проводкою та світлом.",
        )
        User.objects.create(
            email="plumber@ukma.edu.ua",
            password=unusable_password,
            role=resident_role,
            room=room_doorman,
            is_activated=True,
            full_name="Василенко Олег (Сантехнік)",
            position=User.Position.EMPLOYEE,
            bio="Черговий сантехнік гуртожитку. Звертайтеся щодо проблем з трубами чи водою.",
        )

        for f in [3, 5, 6, 7, 8, 9]:
            mod_room = Room.objects.filter(floor__number=f, room_type__type="LIVING").first()
            if mod_room:
                User.objects.create(
                    email=f"moderator{f}@ukma.edu.ua",
                    password=unusable_password,
                    role=moderator_role,
                    room=mod_room,
                    is_activated=True,
                    full_name=f"Староста {f}-го Поверху",
                    major=se_major,
                    position=User.Position.STUDENT,
                    education_level=User.EducationLevel.BACHELOR,
                    year=3,
                    status="Чергую",
                    bio=f"Староста {f}-го поверху. Звертайтеся з будь-якими питаннями щодо порядку.",
                )

        self.stdout.write("Генерація запитів на шеринг...")
        SocialSharingRequest.objects.create(
            creator=u2, title="Позичте праску на годину, дуже треба!", status=active_sharing
        )
        SocialSharingRequest.objects.create(creator=u4, title="Хто має зайву зарядку Type-C?", status=active_sharing)
        SocialSharingRequest.objects.create(creator=u5, title="Потрібна сіль на 5 поверх", status=completed_sharing)
        SocialSharingRequest.objects.create(creator=u1, title="Шукаю HDMI кабель на вечір", status=active_sharing)

        self.stdout.write("Генерація соціальних подій...")
        now = timezone.now()

        event1 = SocialEvent.objects.create(
            creator=u4,
            status=active_sharing,
            title="Вечір настільних ігор",
            description="Граємо в Мафію та Аліас. Приносьте смаколики!",
            start_time=now + timedelta(hours=2),
            end_time=now + timedelta(hours=5),
            max_person=8,
            room=room_41_1,
            floor=room_41_1.floor,
        )
        event1.participants.add(u4, u1, u2, u3)

        event2 = SocialEvent.objects.create(
            creator=u1,
            status=active_sharing,
            title="Ранкова пробіжка",
            description="Біжимо 5 км навколо Подолу. Зустрічаємось біля входу.",
            start_time=(now + timedelta(days=1)).replace(hour=8, minute=0, second=0),
            end_time=(now + timedelta(days=1)).replace(hour=9, minute=0, second=0),
            max_person=0,
            custom_location="Біля головного входу",
        )
        event2.participants.add(u1, u5, admin)

        event3 = SocialEvent.objects.create(
            creator=u2,
            status=active_sharing,
            title="Міні-хакатон від ФІ",
            description="Пишемо пет-проєкти всю ніч. Тільки для своїх з ФІ!",
            start_time=now + timedelta(hours=4),
            end_time=now + timedelta(hours=12),
            max_person=5,
            room=room_42_1,
            floor=room_42_1.floor,
            is_faculty_only=True,
        )
        event3.participants.add(u2, u1)

        event4 = SocialEvent.objects.create(
            creator=u5,
            status=active_sharing,
            title="Спільне приготування піци",
            description="Скидаємось по 100 грн, готуємо на кухні 5 поверху.",
            start_time=(now + timedelta(days=1)).replace(hour=19, minute=0, second=0),
            end_time=(now + timedelta(days=1)).replace(hour=21, minute=30, second=0),
            max_person=4,
            room=kitchen_5,
            floor=kitchen_5.floor,
        )
        event4.participants.add(u5, u6)

        self.stdout.write("Генерація розкладу бронювання...")

        Booking.objects.create(
            user=u1,
            resource=washing_machine_1,
            start_time=now,
            end_time=now + timedelta(hours=2),
            status=active_booking,
        )

        Booking.objects.create(
            user=u4,
            resource=washing_machine_2,
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=3),
            status=active_booking,
        )

        Booking.objects.create(
            user=u5,
            resource=cooktop_1,
            start_time=(now + timedelta(days=1)).replace(hour=19, minute=0, second=0),
            end_time=(now + timedelta(days=1)).replace(hour=21, minute=0, second=0),
            status=active_booking,
        )

        global_target = TargetType.objects.get(type="GLOBAL")
        water_announcement = Announcement.objects.create(
            creator=admin,
            target_type=global_target,
            title="Відключення гарячої води",
            message=(
                "Шановні мешканці! Повідомляємо, що у зв'язку з плановими ремонтними "
                "роботами на теплотрасі, постачання гарячої води в гуртожитку тимчасово призупинено. "
                "Водопостачання буде відновлено наступного тижня. Дякуємо за розуміння!"
            ),
            expires_at=now + timedelta(days=7),
            is_pinned=True,
        )
        Announcement.objects.filter(id=water_announcement.id).update(created_at=now - timedelta(days=7))

        floor_target = TargetType.objects.get(type="FLOOR")
        Announcement.objects.create(
            creator=admin,
            target_type=floor_target,
            target_floor=room_41_1.floor,
            title="Прибирання кухні на 4-му поверсі",
            message=(
                "Шановні мешканці 4-го поверху! Будь ласка, приберіть свої речі з кухонних полиць "
                "до цієї п'ятниці у зв'язку з проведенням планового генерального прибирання та дезінсекції."
            ),
            expires_at=now + timedelta(days=3),
        )

        room_target = TargetType.objects.get(type="ROOM")
        Announcement.objects.create(
            creator=admin,
            target_type=room_target,
            target_room=room_41_2,
            title="Попередження про шум у 41/2",
            message=(
                "Надійшла скарга про порушення тиші після 22:00. Будь ласка, дотримуйтесь "
                "правил внутрішнього розпорядку гуртожитку та поважайте спокій ваших сусідів."
            ),
            expires_at=now + timedelta(days=5),
        )

        self.stdout.write(self.style.SUCCESS("Успішно згенеровано розширені тестові дані для ДЕМО!"))
