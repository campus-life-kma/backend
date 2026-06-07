from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import (
    Announcement,
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
    TargetType,
    User,
)


class RoomBlockApiTests(APITestCase):
    def setUp(self):
        self.dormitory = Dormitory.objects.create(name="Test dormitory")
        self.floor = Floor.objects.create(dormitory=self.dormitory, number=1, map_file="maps/test.svg")
        self.living_type, _ = RoomType.objects.get_or_create(type="LIVING")

        self.active_status, _ = BookingStatus.objects.get_or_create(status="ACTIVE")
        self.cancelled_status, _ = BookingStatus.objects.get_or_create(status="CANCELLED")
        TargetType.objects.get_or_create(type="SPECIFIC_USERS")

        self.room = Room.objects.create(
            floor=self.floor,
            room_type=self.living_type,
            name="101",
            max_person=4,
            svg_element_id="room-101",
        )

        self.washer_type, _ = ResourceType.objects.get_or_create(type="Пральна машина")
        self.resource = Resource.objects.create(
            room=self.room, resource_type=self.washer_type, name="Пралка 1", max_person=1
        )

        self.admin_role, _ = Role.objects.get_or_create(name="ADMIN")
        self.resident_role, _ = Role.objects.get_or_create(name="RESIDENT")

        self.admin = User.objects.create(
            email="admin@ukma.edu.ua", full_name="Admin", role=self.admin_role, is_activated=True
        )
        self.resident = User.objects.create(
            email="resident@ukma.edu.ua",
            full_name="Resident",
            role=self.resident_role,
            room=self.room,
            is_activated=True,
        )

    def test_admin_can_block_room(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(reverse("room-block", args=[self.room.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_blocked"])
        self.room.refresh_from_db()
        self.assertTrue(self.room.is_blocked)

    def test_admin_can_unblock_room(self):
        self.room.is_blocked = True
        self.room.save(update_fields=["is_blocked"])
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(reverse("room-unblock", args=[self.room.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_blocked"])
        self.room.refresh_from_db()
        self.assertFalse(self.room.is_blocked)

    def test_resident_cannot_block_room(self):
        self.client.force_authenticate(user=self.resident)

        response = self.client.patch(reverse("room-block", args=[self.room.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.room.refresh_from_db()
        self.assertFalse(self.room.is_blocked)

    def test_block_requires_authentication(self):
        response = self.client.patch(reverse("room-block", args=[self.room.id]))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_block_returns_404_for_missing_room(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(reverse("room-block", args=[999999]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_block_room_blocks_resources_and_cancels_bookings(self):
        now = timezone.now()
        booking = Booking.objects.create(
            user=self.resident,
            resource=self.resource,
            status=self.active_status,
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
        )
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(reverse("room-block", args=[self.room.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.resource.refresh_from_db()
        self.assertTrue(self.resource.is_blocked)
        booking.refresh_from_db()
        self.assertEqual(booking.status, self.cancelled_status)
        self.assertTrue(Announcement.objects.filter(target_users=self.resident).exists())

    def test_block_room_cancels_events_and_notifies_participants(self):
        now = timezone.now()
        event = SocialEvent.objects.create(
            creator=self.resident,
            room=self.room,
            title="Вечір настолок",
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=3),
            max_person=5,
        )
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(reverse("room-block", args=[self.room.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(SocialEvent.objects.filter(id=event.id).exists())
        self.assertTrue(
            Announcement.objects.filter(target_users=self.resident, title__startswith="Скасування події").exists()
        )

    def test_block_room_notifies_residents(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(reverse("room-block", args=[self.room.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Announcement.objects.filter(target_users=self.resident, title__contains="заблоковано").exists())

    def test_unblock_room_unblocks_resources(self):
        self.room.is_blocked = True
        self.room.save(update_fields=["is_blocked"])
        self.resource.is_blocked = True
        self.resource.save(update_fields=["is_blocked"])
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(reverse("room-unblock", args=[self.room.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.resource.refresh_from_db()
        self.assertFalse(self.resource.is_blocked)
