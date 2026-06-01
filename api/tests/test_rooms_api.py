from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import Dormitory, Floor, Role, Room, RoomType, User


class RoomBlockApiTests(APITestCase):
    def setUp(self):
        self.dormitory = Dormitory.objects.create(name="Test dormitory")
        self.floor = Floor.objects.create(dormitory=self.dormitory, number=1, map_file="maps/test.svg")
        self.living_type, _ = RoomType.objects.get_or_create(type="LIVING")

        self.room = Room.objects.create(
            floor=self.floor,
            room_type=self.living_type,
            name="101",
            max_person=4,
            svg_element_id="room-101",
        )

        self.admin_role, _ = Role.objects.get_or_create(name="ADMIN")
        self.resident_role, _ = Role.objects.get_or_create(name="RESIDENT")

        self.admin = User.objects.create(
            email="admin@ukma.edu.ua", full_name="Admin", role=self.admin_role, is_activated=True
        )
        self.resident = User.objects.create(
            email="resident@ukma.edu.ua", full_name="Resident", role=self.resident_role, is_activated=True
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
