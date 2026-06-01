from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import (
    Dormitory,
    Faculty,
    Floor,
    Major,
    Role,
    Room,
    RoomType,
    SocialEvent,
    SocialSharingRequest,
    SocialSharingStatus,
    User,
)


class SocialsApiTests(APITestCase):
    def setUp(self):
        self.resident_role, _ = Role.objects.get_or_create(name="RESIDENT")
        self.moderator_role, _ = Role.objects.get_or_create(name="MODERATOR")
        self.admin_role, _ = Role.objects.get_or_create(name="ADMIN")

        self.active_status, _ = SocialSharingStatus.objects.get_or_create(status="ACTIVE")
        self.completed_status, _ = SocialSharingStatus.objects.get_or_create(status="COMPLETED")
        self.cancelled_status, _ = SocialSharingStatus.objects.get_or_create(status="CANCELLED")

        self.faculty = Faculty.objects.create(name="Тестовий факультет соціалки")
        self.other_faculty = Faculty.objects.create(name="Інший тестовий факультет соціалки")
        self.major = Major.objects.create(faculty=self.faculty, name="Тестова спеціальність соціалки")
        self.other_major = Major.objects.create(faculty=self.other_faculty, name="Інша тестова спеціальність соціалки")

        self.dormitory = Dormitory.objects.create(name="Тестовий гуртожиток соціалки")
        self.floor = Floor.objects.create(dormitory=self.dormitory, number=1, map_file="maps/socials.svg")
        self.other_floor = Floor.objects.create(dormitory=self.dormitory, number=2, map_file="maps/socials-2.svg")
        self.living_type, _ = RoomType.objects.get_or_create(type="LIVING")
        self.common_type, _ = RoomType.objects.get_or_create(type="COMMON_AREA")

        self.home_room = Room.objects.create(
            floor=self.floor,
            room_type=self.living_type,
            name="101",
            max_person=4,
            svg_element_id="social-room-101",
        )
        self.other_home_room = Room.objects.create(
            floor=self.other_floor,
            room_type=self.living_type,
            name="201",
            max_person=4,
            svg_element_id="social-room-201",
        )
        self.common_room = Room.objects.create(
            floor=self.floor,
            room_type=self.common_type,
            name="Спільна кімната",
            max_person=20,
            svg_element_id="social-common-room",
        )

        self.user = User.objects.create(
            email="social-user@ukma.edu.ua",
            full_name="Соціальний Користувач",
            role=self.resident_role,
            room=self.home_room,
            major=self.major,
            is_activated=True,
        )
        self.other_user = User.objects.create(
            email="other-social-user@ukma.edu.ua",
            full_name="Інший Користувач",
            role=self.resident_role,
            room=self.other_home_room,
            major=self.other_major,
            is_activated=True,
        )
        self.moderator = User.objects.create(
            email="social-moderator@ukma.edu.ua",
            full_name="Модератор Поверху",
            role=self.moderator_role,
            room=self.home_room,
            major=self.major,
            is_activated=True,
        )

        self.client.force_authenticate(user=self.user)

    def create_event(self, creator=None, **kwargs):
        now = timezone.now()
        data = {
            "creator": creator or self.user,
            "title": "Настільні ігри",
            "description": "Граємо ввечері",
            "start_time": now + timedelta(hours=1),
            "end_time": now + timedelta(hours=3),
            "max_person": 5,
            "room": self.common_room,
        }
        data.update(kwargs)
        return SocialEvent.objects.create(**data)

    def test_feed_returns_actual_events_and_active_sharing_requests(self):
        event = self.create_event()
        ongoing_event = self.create_event(
            start_time=timezone.now() - timedelta(hours=1), end_time=timezone.now() + timedelta(hours=1)
        )
        sharing_request = SocialSharingRequest.objects.create(
            creator=self.user,
            title="Позичте зарядку",
            status=self.active_status,
        )
        self.create_event(start_time=timezone.now() - timedelta(hours=3), end_time=timezone.now() - timedelta(hours=1))
        SocialSharingRequest.objects.create(
            creator=self.user,
            title="Вже неактивний запит",
            status=self.completed_status,
        )

        response = self.client.get(reverse("feed", kwargs={"page": 1}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = {(item["type"], item["id"]) for item in response.data["results"]}
        self.assertIn(("event", event.id), result_ids)
        self.assertIn(("event", ongoing_event.id), result_ids)
        self.assertIn(("sharing_request", sharing_request.id), result_ids)
        self.assertEqual(len(response.data["results"]), 3)

    def test_feed_hides_foreign_faculty_only_events(self):
        hidden_event = self.create_event(creator=self.other_user, is_faculty_only=True)
        visible_event = self.create_event(creator=self.user, is_faculty_only=True)

        response = self.client.get(reverse("feed", kwargs={"page": 1}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event_ids = [item["id"] for item in response.data["results"] if item["type"] == "event"]
        self.assertIn(visible_event.id, event_ids)
        self.assertNotIn(hidden_event.id, event_ids)

    def test_create_event_adds_creator_to_participants(self):
        now = timezone.now()
        response = self.client.post(
            reverse("event-create"),
            {
                "title": "Мафія",
                "description": "Збираємось у спільній кімнаті",
                "start_time": (now + timedelta(hours=1)).isoformat(),
                "end_time": (now + timedelta(hours=2)).isoformat(),
                "max_person": 8,
                "room": self.common_room.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event = SocialEvent.objects.get(id=response.data["id"])
        self.assertTrue(event.participants.filter(id=self.user.id).exists())

    def test_get_event_detail_returns_participants(self):
        event = self.create_event()
        event.participants.add(self.user, self.other_user)

        response = self.client.get(reverse("event-detail", kwargs={"event_id": event.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        participant_ids = {participant["id"] for participant in response.data["participants"]}
        self.assertNotIn("participants_count", response.data)
        self.assertEqual(len(response.data["participants"]), 2)
        self.assertIn(str(self.user.id), participant_ids)
        self.assertIn(str(self.other_user.id), participant_ids)

    def test_create_event_requires_location(self):
        now = timezone.now()
        response = self.client.post(
            reverse("event-create"),
            {
                "title": "Подія без місця",
                "description": "Не має пройти",
                "start_time": (now + timedelta(hours=1)).isoformat(),
                "end_time": (now + timedelta(hours=2)).isoformat(),
                "max_person": 8,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_join_event_respects_max_person(self):
        event = self.create_event(max_person=1)
        event.participants.add(self.other_user)

        response = self.client.post(reverse("event-join", kwargs={"event_id": event.id}))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(event.participants.filter(id=self.user.id).exists())

    def test_join_and_leave_event(self):
        event = self.create_event(max_person=2)

        join_response = self.client.post(reverse("event-join", kwargs={"event_id": event.id}))
        leave_response = self.client.post(reverse("event-leave", kwargs={"event_id": event.id}))

        self.assertEqual(join_response.status_code, status.HTTP_200_OK)
        self.assertEqual(leave_response.status_code, status.HTTP_200_OK)
        self.assertFalse(event.participants.filter(id=self.user.id).exists())

    def test_create_and_complete_sharing_request(self):
        create_response = self.client.post(
            reverse("sharing-request-create"),
            {"title": "Позичте сіль"},
            format="json",
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        request_id = create_response.data["id"]
        done_response = self.client.patch(reverse("sharing-request-done", kwargs={"request_id": request_id}))

        self.assertEqual(done_response.status_code, status.HTTP_200_OK)
        self.assertEqual(done_response.data["status"], "COMPLETED")

    def test_moderator_can_delete_sharing_request_on_own_floor(self):
        sharing_request = SocialSharingRequest.objects.create(
            creator=self.user,
            title="Потрібен подовжувач",
            status=self.active_status,
        )
        self.client.force_authenticate(user=self.moderator)

        response = self.client.delete(reverse("sharing-request-detail", kwargs={"request_id": sharing_request.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sharing_request.refresh_from_db()
        self.assertEqual(sharing_request.status.status, "CANCELLED")

    def test_user_cannot_delete_other_users_event(self):
        event = self.create_event(creator=self.other_user)

        response = self.client.delete(reverse("event-detail", kwargs={"event_id": event.id}))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(SocialEvent.objects.filter(id=event.id).exists())

    def test_owner_can_update_event(self):
        event = self.create_event(creator=self.user)
        new_title = "Оновлена назва події"

        response = self.client.patch(
            reverse("event-detail", kwargs={"event_id": event.id}), {"title": new_title}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertEqual(event.title, new_title)

    def test_other_user_cannot_update_event(self):
        event = self.create_event(creator=self.other_user)

        response = self.client.patch(
            reverse("event-detail", kwargs={"event_id": event.id}), {"title": "Хакерська зміна"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        event.refresh_from_db()
        self.assertNotEqual(event.title, "Хакерська зміна")

    def test_owner_can_update_sharing_request(self):
        request = SocialSharingRequest.objects.create(creator=self.user, title="Стара назва", status=self.active_status)

        response = self.client.patch(
            reverse("sharing-request-detail", kwargs={"request_id": request.id}), {"title": "Нова назва"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        request.refresh_from_db()
        self.assertEqual(request.title, "Нова назва")

    def test_other_user_cannot_update_sharing_request(self):
        request = SocialSharingRequest.objects.create(
            creator=self.other_user, title="Стара назва", status=self.active_status
        )

        response = self.client.patch(
            reverse("sharing-request-detail", kwargs={"request_id": request.id}),
            {"title": "Зламана назва"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
