from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import Dormitory, Faculty, Floor, Major, Role, Room, RoomType, User


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class UsersApiTests(APITestCase):
    def setUp(self):
        self.resident_role, _ = Role.objects.get_or_create(name="RESIDENT")
        self.admin_role, _ = Role.objects.get_or_create(name="ADMIN")
        self.moderator_role, _ = Role.objects.get_or_create(name="MODERATOR")

        self.faculty = Faculty.objects.create(name="Факультет тестування профілів")
        self.major = Major.objects.create(faculty=self.faculty, name="Тестова спеціальність профілів")
        self.other_major = Major.objects.create(faculty=self.faculty, name="Інша тестова спеціальність")

        self.dormitory = Dormitory.objects.create(name="Гуртожиток профілів")
        self.floor = Floor.objects.create(dormitory=self.dormitory, number=1, map_file="maps/users-1.svg")
        self.other_floor = Floor.objects.create(dormitory=self.dormitory, number=2, map_file="maps/users-2.svg")
        self.living_type, _ = RoomType.objects.get_or_create(type="LIVING")
        self.common_type, _ = RoomType.objects.get_or_create(type="COMMON_AREA")

        self.room = Room.objects.create(
            floor=self.floor,
            room_type=self.living_type,
            name="101",
            max_person=2,
            svg_element_id="user-room-101",
        )
        self.full_room = Room.objects.create(
            floor=self.floor,
            room_type=self.living_type,
            name="102",
            max_person=1,
            svg_element_id="user-room-102",
        )
        self.available_room = Room.objects.create(
            floor=self.other_floor,
            room_type=self.living_type,
            name="202",
            max_person=2,
            svg_element_id="user-room-202",
        )
        self.blocked_room = Room.objects.create(
            floor=self.other_floor,
            room_type=self.living_type,
            name="201",
            max_person=2,
            is_blocked=True,
            svg_element_id="user-room-201",
        )
        self.common_room = Room.objects.create(
            floor=self.floor,
            room_type=self.common_type,
            name="Кімната відпочинку",
            max_person=10,
            svg_element_id="user-common-room",
        )

        self.admin = User.objects.create(
            email="users-admin@ukma.edu.ua",
            full_name="Адмін Профілів",
            role=self.admin_role,
            room=self.room,
            is_activated=True,
        )
        self.moderator = User.objects.create(
            email="users-moderator@ukma.edu.ua",
            full_name="Модератор Профілів",
            role=self.moderator_role,
            room=self.room,
            is_activated=True,
        )
        self.user = User.objects.create(
            email="profile-user@ukma.edu.ua",
            full_name="Користувач Профілю",
            role=self.resident_role,
            room=self.room,
            major=self.major,
            year=1,
            status="Старий статус",
            bio="Старе біо",
            is_activated=True,
        )
        self.full_room_resident = User.objects.create(
            email="full-room-user@ukma.edu.ua",
            full_name="Мешканець Повної Кімнати",
            role=self.resident_role,
            room=self.full_room,
            is_activated=True,
        )
        self.other_floor_user = User.objects.create(
            email="other-floor-profile-user@ukma.edu.ua",
            full_name="Мешканець Іншого Поверху",
            role=self.resident_role,
            room=self.available_room,
            is_activated=True,
        )
        self.client.force_authenticate(user=self.admin)

    def test_admin_can_update_user_profile_and_user_receives_email(self):
        response = self.client.patch(
            reverse("user-info", args=[self.user.id]),
            {
                "full_name": "Оновлений Користувач",
                "role": self.moderator_role.id,
                "room": self.available_room.id,
                "major": self.other_major.id,
                "education_level": User.EducationLevel.MASTER,
                "year": 2,
                "status": "Новий статус",
                "bio": "Нове біо",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Оновлений Користувач")
        self.assertEqual(self.user.role, self.moderator_role)
        self.assertEqual(self.user.room, self.available_room)
        self.assertEqual(self.user.education_level, User.EducationLevel.MASTER)
        self.assertEqual(self.user.year, 2)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Кімната проживання", mail.outbox[0].body)
        self.assertIn("Рівень навчання", mail.outbox[0].body)
        self.assertIn("Магістр", mail.outbox[0].body)
        self.assertIn("Оновлений Користувач", mail.outbox[0].body)

    def test_admin_cannot_set_invalid_master_year(self):
        response = self.client.patch(
            reverse("user-info", args=[self.user.id]),
            {
                "education_level": User.EducationLevel.MASTER,
                "year": 3,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["year"][0], "Для магістратури можна вказати лише 1 або 2 курс.")

    def test_admin_can_set_phd_year(self):
        response = self.client.patch(
            reverse("user-info", args=[self.user.id]),
            {
                "education_level": User.EducationLevel.PHD,
                "year": 4,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.education_level, User.EducationLevel.PHD)
        self.assertEqual(self.user.year, 4)

    def test_moderator_can_update_status_and_bio_for_user_on_own_floor(self):
        self.client.force_authenticate(user=self.moderator)

        response = self.client.patch(
            reverse("user-info", args=[self.user.id]),
            {"status": "Оновлено модератором", "bio": "Біо після модерації"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.status, "Оновлено модератором")
        self.assertEqual(self.user.bio, "Біо після модерації")

    def test_moderator_cannot_update_other_profile_fields(self):
        self.client.force_authenticate(user=self.moderator)

        response = self.client.patch(
            reverse("user-info", args=[self.user.id]),
            {"full_name": "Не можна", "status": "Можна"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.full_name, "Не можна")
        self.assertNotEqual(self.user.status, "Можна")

    def test_moderator_cannot_update_profile_on_other_floor(self):
        self.client.force_authenticate(user=self.moderator)

        response = self.client.patch(
            reverse("user-info", args=[self.other_floor_user.id]),
            {"status": "Чужий поверх"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.other_floor_user.refresh_from_db()
        self.assertNotEqual(self.other_floor_user.status, "Чужий поверх")

    def test_admin_cannot_move_user_to_full_room(self):
        other_user = User.objects.create(
            email="other-profile-user@ukma.edu.ua",
            full_name="Інший Користувач",
            role=self.resident_role,
            room=self.room,
            is_activated=True,
        )

        response = self.client.patch(
            reverse("user-info", args=[other_user.id]),
            {"room": self.full_room.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["room"][0], "У цій кімнаті немає вільних місць.")
        other_user.refresh_from_db()
        self.assertEqual(other_user.room, self.room)

    def test_admin_cannot_move_user_to_blocked_room(self):
        response = self.client.patch(
            reverse("user-info", args=[self.user.id]),
            {"room": self.blocked_room.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["room"][0], "Ця кімната заблокована, тому поселення в неї недоступне.")

    def test_admin_cannot_move_user_to_non_living_room(self):
        response = self.client.patch(
            reverse("user-info", args=[self.user.id]),
            {"room": self.common_room.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["room"][0], "Користувача можна поселити лише в житлову кімнату.")
