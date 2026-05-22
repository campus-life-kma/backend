from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import Booking, BookingStatus, Dormitory, Floor, Resource, Role, Room, RoomType, User


class BookingsApiTests(APITestCase):
    def setUp(self):
        self.resident_role, _ = Role.objects.get_or_create(name="RESIDENT")
        self.moderator_role, _ = Role.objects.get_or_create(name="MODERATOR")
        self.admin_role, _ = Role.objects.get_or_create(name="ADMIN")

        self.active_status, _ = BookingStatus.objects.get_or_create(status="ACTIVE")
        self.cancelled_status, _ = BookingStatus.objects.get_or_create(status="CANCELLED")
        self.completed_status, _ = BookingStatus.objects.get_or_create(status="COMPLETED")

        self.dormitory = Dormitory.objects.create(name="Тестовий гуртожиток бронювань")
        self.floor = Floor.objects.create(dormitory=self.dormitory, number=1, map_file="maps/bookings-1.svg")
        self.other_floor = Floor.objects.create(dormitory=self.dormitory, number=2, map_file="maps/bookings-2.svg")
        self.living_type, _ = RoomType.objects.get_or_create(type="LIVING")
        self.laundry_type, _ = RoomType.objects.get_or_create(type="LAUNDRY")

        self.home_room = Room.objects.create(
            floor=self.floor,
            room_type=self.living_type,
            name="101",
            max_person=4,
            svg_element_id="booking-room-101",
        )
        self.other_home_room = Room.objects.create(
            floor=self.other_floor,
            room_type=self.living_type,
            name="201",
            max_person=4,
            svg_element_id="booking-room-201",
        )
        self.laundry_room = Room.objects.create(
            floor=self.floor,
            room_type=self.laundry_type,
            name="Пральня 1",
            max_person=5,
            svg_element_id="booking-laundry-1",
        )
        self.other_laundry_room = Room.objects.create(
            floor=self.other_floor,
            room_type=self.laundry_type,
            name="Пральня 2",
            max_person=5,
            svg_element_id="booking-laundry-2",
        )

        self.resource = Resource.objects.create(
            room=self.laundry_room,
            name="Пральна машина 1",
            max_person=1,
        )
        self.shared_resource = Resource.objects.create(
            room=self.laundry_room,
            name="Сушильна машина 1",
            max_person=2,
        )
        self.other_resource = Resource.objects.create(
            room=self.other_laundry_room,
            name="Пральна машина 2",
            max_person=1,
        )

        self.user = User.objects.create(
            email="booking-user@ukma.edu.ua",
            full_name="Користувач Бронювання",
            role=self.resident_role,
            room=self.home_room,
            is_activated=True,
        )
        self.other_user = User.objects.create(
            email="other-booking-user@ukma.edu.ua",
            full_name="Інший Користувач",
            role=self.resident_role,
            room=self.other_home_room,
            is_activated=True,
        )
        self.moderator = User.objects.create(
            email="booking-moderator@ukma.edu.ua",
            full_name="Голова Поверху",
            role=self.moderator_role,
            room=self.home_room,
            is_activated=True,
        )
        self.admin = User.objects.create(
            email="booking-admin@ukma.edu.ua",
            full_name="Адміністратор",
            role=self.admin_role,
            room=self.other_home_room,
            is_activated=True,
        )

        self.client.force_authenticate(user=self.user)

    def future_range(self, hours_from_now=2, duration_hours=1):
        start_time = timezone.now() + timedelta(hours=hours_from_now)
        end_time = start_time + timedelta(hours=duration_hours)
        return start_time, end_time

    def create_booking(self, user=None, resource=None, start_time=None, end_time=None, status_obj=None):
        if not start_time or not end_time:
            start_time, end_time = self.future_range()

        return Booking.objects.create(
            user=user or self.user,
            resource=resource or self.resource,
            start_time=start_time,
            end_time=end_time,
            status=status_obj or self.active_status,
        )

    def test_create_booking_success(self):
        start_time, end_time = self.future_range()

        response = self.client.post(
            reverse("booking-create"),
            {
                "resource": self.resource.id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["resource_id"], self.resource.id)
        self.assertEqual(response.data["status"], "ACTIVE")

    def test_create_booking_rejects_blocked_resource(self):
        self.resource.is_blocked = True
        self.resource.save(update_fields=["is_blocked"])
        start_time, end_time = self.future_range()

        response = self.client.post(
            reverse("booking-create"),
            {
                "resource": self.resource.id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_booking_rejects_overlap_when_resource_is_full(self):
        start_time, end_time = self.future_range()
        self.create_booking(user=self.other_user, start_time=start_time, end_time=end_time)

        response = self.client.post(
            reverse("booking-create"),
            {
                "resource": self.resource.id,
                "start_time": (start_time + timedelta(minutes=15)).isoformat(),
                "end_time": (end_time + timedelta(minutes=15)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_booking_allows_adjacent_slots(self):
        start_time, end_time = self.future_range()
        self.create_booking(user=self.other_user, start_time=start_time, end_time=end_time)

        response = self.client.post(
            reverse("booking-create"),
            {
                "resource": self.resource.id,
                "start_time": end_time.isoformat(),
                "end_time": (end_time + timedelta(hours=1)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_booking_allows_parallel_until_max_person(self):
        start_time, end_time = self.future_range()
        self.create_booking(
            user=self.other_user, resource=self.shared_resource, start_time=start_time, end_time=end_time
        )

        response = self.client.post(
            reverse("booking-create"),
            {
                "resource": self.shared_resource.id,
                "start_time": (start_time + timedelta(minutes=10)).isoformat(),
                "end_time": (end_time - timedelta(minutes=10)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_booking_rejects_past_start_time(self):
        start_time = timezone.now() - timedelta(hours=1)
        end_time = timezone.now() + timedelta(hours=1)

        response = self.client.post(
            reverse("booking-create"),
            {
                "resource": self.resource.id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resource_schedule_returns_active_bookings_for_today_and_tomorrow(self):
        active_booking = self.create_booking()
        self.create_booking(status_obj=self.cancelled_status)

        response = self.client.get(reverse("resource-schedule", kwargs={"resource_id": self.resource.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["booking_id"], active_booking.id)

    def test_my_bookings_returns_only_my_future_active_bookings(self):
        my_booking = self.create_booking()
        self.create_booking(user=self.other_user)
        self.create_booking(status_obj=self.cancelled_status)

        response = self.client.get(reverse("bookings-me"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], my_booking.id)

    def test_resident_can_cancel_own_booking(self):
        booking = self.create_booking()

        response = self.client.patch(reverse("booking-cancel", kwargs={"booking_id": booking.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status.status, "CANCELLED")

    def test_resident_cannot_cancel_other_users_booking(self):
        booking = self.create_booking(user=self.other_user)

        response = self.client.patch(reverse("booking-cancel", kwargs={"booking_id": booking.id}))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_can_cancel_booking_on_own_floor(self):
        booking = self.create_booking(user=self.other_user, resource=self.resource)
        self.client.force_authenticate(user=self.moderator)

        response = self.client.patch(reverse("booking-cancel", kwargs={"booking_id": booking.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status.status, "CANCELLED")

    def test_moderator_cannot_cancel_booking_on_other_floor(self):
        booking = self.create_booking(user=self.other_user, resource=self.other_resource)
        self.client.force_authenticate(user=self.moderator)

        response = self.client.patch(reverse("booking-cancel", kwargs={"booking_id": booking.id}))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_block_resource_and_cancel_future_bookings(self):
        booking = self.create_booking(resource=self.resource)
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(reverse("resource-block", kwargs={"resource_id": self.resource.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.resource.refresh_from_db()
        booking.refresh_from_db()
        self.assertTrue(self.resource.is_blocked)
        self.assertEqual(booking.status.status, "CANCELLED")
        self.assertEqual(response.data["cancelled_bookings_count"], 1)

    def test_non_admin_cannot_block_resource(self):
        response = self.client.patch(reverse("resource-block", kwargs={"resource_id": self.resource.id}))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_unblock_resource(self):
        self.resource.is_blocked = True
        self.resource.save(update_fields=["is_blocked"])
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(reverse("resource-unblock", kwargs={"resource_id": self.resource.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.resource.refresh_from_db()
        self.assertFalse(self.resource.is_blocked)
