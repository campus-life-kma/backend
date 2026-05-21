from datetime import timedelta

from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import Announcement, AnnouncementRead, Dormitory, Floor, Role, Room, RoomType, TargetType, User


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AnnouncementsApiTests(APITestCase):
    def setUp(self):
        self.resident_role, _ = Role.objects.get_or_create(name="RESIDENT")
        self.moderator_role, _ = Role.objects.get_or_create(name="MODERATOR")
        self.admin_role, _ = Role.objects.get_or_create(name="ADMIN")

        self.global_type, _ = TargetType.objects.get_or_create(type="GLOBAL")
        self.floor_type, _ = TargetType.objects.get_or_create(type="FLOOR")
        self.room_type_target, _ = TargetType.objects.get_or_create(type="ROOM")
        self.specific_users_type, _ = TargetType.objects.get_or_create(type="SPECIFIC_USERS")

        self.dormitory = Dormitory.objects.create(name="Тестовий гуртожиток оголошень")
        self.floor = Floor.objects.create(dormitory=self.dormitory, number=1, map_file="maps/announcements-1.svg")
        self.other_floor = Floor.objects.create(dormitory=self.dormitory, number=2, map_file="maps/announcements-2.svg")
        self.living_type, _ = RoomType.objects.get_or_create(type="LIVING")

        self.room = Room.objects.create(
            floor=self.floor,
            room_type=self.living_type,
            name="101",
            max_person=4,
            svg_element_id="announcement-room-101",
        )
        self.other_room = Room.objects.create(
            floor=self.other_floor,
            room_type=self.living_type,
            name="201",
            max_person=4,
            svg_element_id="announcement-room-201",
        )

        self.user = User.objects.create(
            email="announcement-user@ukma.edu.ua",
            full_name="Користувач Оголошень",
            role=self.resident_role,
            room=self.room,
            is_activated=True,
        )
        self.other_user = User.objects.create(
            email="other-announcement-user@ukma.edu.ua",
            full_name="Інший Користувач",
            role=self.resident_role,
            room=self.other_room,
            is_activated=True,
        )
        self.moderator = User.objects.create(
            email="announcement-moderator@ukma.edu.ua",
            full_name="Голова Поверху",
            role=self.moderator_role,
            room=self.room,
            is_activated=True,
        )
        self.admin = User.objects.create(
            email="announcement-admin@ukma.edu.ua",
            full_name="Адміністратор",
            role=self.admin_role,
            room=self.other_room,
            is_activated=True,
        )

        self.client.force_authenticate(user=self.user)

    def create_announcement(self, target_type=None, creator=None, **kwargs):
        data = {
            "creator": creator or self.admin,
            "target_type": target_type or self.global_type,
            "title": "Важливе оголошення",
            "message": "Текст оголошення",
        }
        data.update(kwargs)
        return Announcement.objects.create(**data)

    def test_active_announcements_include_matching_targets(self):
        global_announcement = self.create_announcement(title="Глобальне")
        floor_announcement = self.create_announcement(
            target_type=self.floor_type,
            target_floor=self.floor,
            title="Для поверху",
        )
        room_announcement = self.create_announcement(
            target_type=self.room_type_target,
            target_room=self.room,
            title="Для кімнати",
        )
        specific_announcement = self.create_announcement(
            target_type=self.specific_users_type,
            title="Для користувача",
        )
        specific_announcement.target_users.add(self.user)

        self.create_announcement(target_type=self.floor_type, target_floor=self.other_floor, title="Чужий поверх")
        self.create_announcement(target_type=self.room_type_target, target_room=self.other_room, title="Чужа кімната")

        response = self.client.get(reverse("announcements-active"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in response.data}
        self.assertIn(global_announcement.id, ids)
        self.assertIn(floor_announcement.id, ids)
        self.assertIn(room_announcement.id, ids)
        self.assertIn(specific_announcement.id, ids)
        self.assertEqual(len(response.data), 4)

    def test_read_null_expires_announcement_disappears_from_active(self):
        announcement = self.create_announcement(expires_at=None)

        read_response = self.client.post(reverse("announcement-read", kwargs={"announcement_id": announcement.id}))
        active_response = self.client.get(reverse("announcements-active"))

        self.assertEqual(read_response.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in active_response.data}
        self.assertNotIn(announcement.id, ids)

    def test_read_is_idempotent(self):
        announcement = self.create_announcement()

        first_response = self.client.post(reverse("announcement-read", kwargs={"announcement_id": announcement.id}))
        second_response = self.client.post(reverse("announcement-read", kwargs={"announcement_id": announcement.id}))

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(AnnouncementRead.objects.filter(announcement=announcement, user=self.user).count(), 1)

    def test_expired_announcement_is_not_active(self):
        announcement = self.create_announcement(expires_at=timezone.now() - timedelta(minutes=1))

        response = self.client.get(reverse("announcements-active"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in response.data}
        self.assertNotIn(announcement.id, ids)

    def test_read_foreign_announcement_returns_403(self):
        announcement = self.create_announcement(target_type=self.floor_type, target_floor=self.other_floor)

        response = self.client.post(reverse("announcement-read", kwargs={"announcement_id": announcement.id}))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_resident_cannot_create_announcement(self):
        response = self.client.post(
            reverse("announcement-create"),
            {
                "title": "Оголошення",
                "message": "Текст",
                "target_type": "GLOBAL",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_can_create_floor_announcement_for_own_floor(self):
        self.client.force_authenticate(user=self.moderator)

        response = self.client.post(
            reverse("announcement-create"),
            {
                "title": "Прибирання",
                "message": "Сьогодні прибирання кухні",
                "target_type": "FLOOR",
                "target_floor": self.floor.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["target_type"], "FLOOR")
        self.assertEqual(response.data["target_floor_id"], self.floor.id)
        self.assertEqual(len(mail.outbox), 2)
        recipients = {message.to[0] for message in mail.outbox}
        self.assertEqual(recipients, {self.user.email, self.moderator.email})

    def test_moderator_cannot_create_global_announcement(self):
        self.client.force_authenticate(user=self.moderator)

        response = self.client.post(
            reverse("announcement-create"),
            {
                "title": "Глобальне",
                "message": "Не має пройти",
                "target_type": "GLOBAL",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_specific_users_announcement(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse("announcement-create"),
            {
                "title": "Особисте",
                "message": "Повідомлення для конкретного мешканця",
                "target_type": "SPECIFIC_USERS",
                "target_users": [str(self.user.id)],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["target_type"], "SPECIFIC_USERS")
        self.assertEqual(response.data["target_user_ids"], [str(self.user.id)])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    def test_create_rejects_past_expires_at(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse("announcement-create"),
            {
                "title": "Прострочене",
                "message": "Не має пройти",
                "target_type": "GLOBAL",
                "expires_at": (timezone.now() - timedelta(minutes=1)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)

    def test_admin_global_announcement_sends_email_to_active_users(self):
        inactive_user = User.objects.create(
            email="inactive-announcement-user@ukma.edu.ua",
            full_name="Неактивований Користувач",
            role=self.resident_role,
            room=self.room,
            is_activated=False,
        )
        disabled_user = User.objects.create(
            email="disabled-announcement-user@ukma.edu.ua",
            full_name="Деактивований Користувач",
            role=self.resident_role,
            room=self.room,
            is_active=False,
            is_activated=True,
        )
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse("announcement-create"),
            {
                "title": "Глобальна розсилка",
                "message": "Повідомлення для всіх активованих користувачів",
                "target_type": "GLOBAL",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipients = {message.to[0] for message in mail.outbox}
        self.assertTrue(
            {
                self.user.email,
                self.other_user.email,
                self.moderator.email,
                self.admin.email,
                inactive_user.email,
            }
            <= recipients
        )
        self.assertNotIn(disabled_user.email, recipients)
        self.assertTrue(all("Campus Life: Глобальна розсилка" == message.subject for message in mail.outbox))
