from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import Dormitory, Floor, Presence, Room, RoomType, User


class PresenceApiTests(APITestCase):
    def setUp(self):
        self.dormitory = Dormitory.objects.create(name="Test dormitory")
        self.floor = Floor.objects.create(dormitory=self.dormitory, number=1, map_file="maps/test.svg")
        self.living_type, _ = RoomType.objects.get_or_create(type="LIVING")
        self.common_type, _ = RoomType.objects.get_or_create(type="COMMON_AREA")

        self.home_room = Room.objects.create(
            floor=self.floor,
            room_type=self.living_type,
            name="101",
            max_person=4,
            svg_element_id="room-101",
        )
        self.common_room = Room.objects.create(
            floor=self.floor,
            room_type=self.common_type,
            name="Common room",
            max_person=10,
            svg_element_id="common-room",
        )
        self.second_common_room = Room.objects.create(
            floor=self.floor,
            room_type=self.common_type,
            name="Second common room",
            max_person=10,
            svg_element_id="second-common-room",
        )
        self.blocked_room = Room.objects.create(
            floor=self.floor,
            room_type=self.common_type,
            name="Blocked common room",
            max_person=10,
            svg_element_id="blocked-common-room",
            is_blocked=True,
        )
        self.user = User.objects.create(
            email="resident@ukma.edu.ua",
            full_name="Resident User",
            room=self.home_room,
            is_activated=True,
        )

        self.client.force_authenticate(user=self.user)

    def test_check_in_creates_presence(self):
        response = self.client.post(reverse("presence-check-in"), {"room_id": self.common_room.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Presence.objects.count(), 1)

        presence = Presence.objects.get(user=self.user)
        self.assertEqual(presence.room, self.common_room)
        self.assertLess(presence.joined_at, presence.expires_at)
        self.assertEqual(response.data["room_id"], self.common_room.id)

    def test_check_in_updates_existing_presence(self):
        old_joined_at = timezone.now() - timedelta(hours=1)
        Presence.objects.create(
            user=self.user,
            room=self.common_room,
            joined_at=old_joined_at,
            expires_at=old_joined_at + timedelta(hours=2),
        )

        response = self.client.post(
            reverse("presence-check-in"), {"room_id": self.second_common_room.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Presence.objects.count(), 1)

        presence = Presence.objects.get(user=self.user)
        self.assertEqual(presence.room, self.second_common_room)
        self.assertGreater(presence.joined_at, old_joined_at)

    def test_go_home_deletes_presence(self):
        now = timezone.now()
        Presence.objects.create(
            user=self.user,
            room=self.common_room,
            joined_at=now,
            expires_at=now + timedelta(hours=2),
        )

        response = self.client.post(reverse("presence-go-home"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Presence.objects.filter(user=self.user).exists())

    def test_check_in_rejects_blocked_room(self):
        response = self.client.post(reverse("presence-check-in"), {"room_id": self.blocked_room.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Presence.objects.filter(user=self.user).exists())

    def test_check_in_allows_living_room(self):
        response = self.client.post(reverse("presence-check-in"), {"room_id": self.home_room.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Presence.objects.count(), 1)

        presence = Presence.objects.get(user=self.user)
        self.assertEqual(presence.room, self.home_room)
        self.assertEqual(response.data["room_id"], self.home_room.id)

    def test_check_in_returns_404_for_missing_room(self):
        response = self.client.post(reverse("presence-check-in"), {"room_id": 999999}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_check_in_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(reverse("presence-check-in"), {"room_id": self.common_room.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
