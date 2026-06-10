from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import (
    Booking,
    BookingStatus,
    Dormitory,
    Floor,
    Resource,
    ResourceType,
    Role,
    Room,
    RoomType,
    SocialEvent,
    SocialSharingRequest,
    SocialSharingStatus,
    User,
)


class StatisticsApiTests(APITestCase):
    def setUp(self):
        self.resident_role, _ = Role.objects.get_or_create(name="RESIDENT")
        self.admin_role, _ = Role.objects.get_or_create(name="ADMIN")
        self.moderator_role, _ = Role.objects.get_or_create(name="MODERATOR")
        self.active_booking_status, _ = BookingStatus.objects.get_or_create(status="ACTIVE")
        self.cancelled_booking_status, _ = BookingStatus.objects.get_or_create(status="CANCELLED")
        self.active_social_status, _ = SocialSharingStatus.objects.get_or_create(status="ACTIVE")
        self.completed_social_status, _ = SocialSharingStatus.objects.get_or_create(status="COMPLETED")

        self.dormitory = Dormitory.objects.create(name="Маккейна")
        self.first_floor = Floor.objects.create(dormitory=self.dormitory, number=4, map_file="maps/stat-4.svg")
        self.second_floor = Floor.objects.create(dormitory=self.dormitory, number=5, map_file="maps/stat-5.svg")
        self.living_type, _ = RoomType.objects.get_or_create(type="LIVING")
        self.common_type, _ = RoomType.objects.get_or_create(type="COMMON_AREA")
        self.resource_type = ResourceType.objects.create(type="Пральна машина", icon_file="icons/washer.svg")

        self.admin_room = Room.objects.create(
            floor=self.first_floor,
            room_type=self.living_type,
            name="401",
            max_person=2,
            svg_element_id="stat-room-401",
        )
        self.moderator_room = Room.objects.create(
            floor=self.first_floor,
            room_type=self.living_type,
            name="402",
            max_person=1,
            svg_element_id="stat-room-402",
        )
        self.other_floor_room = Room.objects.create(
            floor=self.second_floor,
            room_type=self.living_type,
            name="501",
            max_person=2,
            svg_element_id="stat-room-501",
        )
        self.resource_room = Room.objects.create(
            floor=self.first_floor,
            room_type=self.common_type,
            name="Пральня",
            max_person=4,
            svg_element_id="stat-laundry",
        )
        self.resource = Resource.objects.create(
            room=self.resource_room,
            resource_type=self.resource_type,
            name="Пральна машина 1",
            max_person=1,
        )

        self.admin = User.objects.create(
            email="statistics-admin@ukma.edu.ua",
            full_name="Адмін статистики",
            role=self.admin_role,
            room=self.admin_room,
            is_activated=True,
        )
        self.moderator = User.objects.create(
            email="statistics-moderator@ukma.edu.ua",
            full_name="Модератор статистики",
            role=self.moderator_role,
            room=self.moderator_room,
            is_activated=True,
        )
        self.resident = User.objects.create(
            email="statistics-resident@ukma.edu.ua",
            full_name="Мешканець статистики",
            role=self.resident_role,
            room=self.moderator_room,
            is_activated=True,
        )
        self.other_floor_resident = User.objects.create(
            email="statistics-other-floor@ukma.edu.ua",
            full_name="Інший поверх",
            role=self.resident_role,
            room=self.other_floor_room,
            is_activated=True,
        )
        self.not_activated_user = User.objects.create(
            email="statistics-new@ukma.edu.ua",
            full_name="Не активований",
            role=self.resident_role,
            room=self.other_floor_room,
            is_activated=False,
        )

        now = timezone.now()
        Booking.objects.create(
            user=self.resident,
            resource=self.resource,
            start_time=now + timezone.timedelta(hours=1),
            end_time=now + timezone.timedelta(hours=2),
            status=self.active_booking_status,
        )
        Booking.objects.create(
            user=self.resident,
            resource=self.resource,
            start_time=now + timezone.timedelta(days=1),
            end_time=now + timezone.timedelta(days=1, hours=1),
            status=self.cancelled_booking_status,
            cancelled_by=self.moderator,
        )
        SocialEvent.objects.create(
            creator=self.resident,
            status=self.active_social_status,
            floor=self.first_floor,
            title="Настільні ігри",
            start_time=now + timezone.timedelta(hours=1),
            end_time=now + timezone.timedelta(hours=3),
            max_person=0,
        )
        SocialSharingRequest.objects.create(
            creator=self.other_floor_resident,
            title="Позичте сіль",
            status=self.completed_social_status,
        )

    def test_admin_can_get_dormitory_statistics(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(reverse("statistics-summary"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["scope"]["type"], "DORMITORY")
        self.assertEqual(response.data["residents"]["total"], 5)
        self.assertEqual(response.data["residents"]["activated"], 4)
        self.assertEqual(response.data["bookings"]["active"], 1)
        self.assertEqual(response.data["bookings"]["cancelled_by_moderators"], 1)
        self.assertEqual(response.data["social"]["active_events"], 1)
        self.assertEqual(response.data["social"]["completed_sharing_requests"], 1)
        self.assertEqual(response.data["bookings"]["top_resources"][0]["resource_name"], "Пральна машина 1")

    def test_moderator_gets_only_own_floor_statistics(self):
        self.client.force_authenticate(user=self.moderator)

        response = self.client.get(reverse("statistics-summary"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["scope"]["type"], "FLOOR")
        self.assertEqual(response.data["scope"]["floor_id"], self.first_floor.id)
        self.assertEqual(response.data["residents"]["total"], 3)
        self.assertEqual(response.data["social"]["completed_sharing_requests"], 0)
        self.assertEqual(len(response.data["social"]["floor_activity"]), 1)

    def test_resident_cannot_get_statistics(self):
        self.client.force_authenticate(user=self.resident)

        response = self.client.get(reverse("statistics-summary"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Статистика доступна лише адміністраторам і модераторам.")
