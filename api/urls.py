from django.conf import settings
from django.urls import path

from api.views.announcements_view import (
    ActiveAnnouncementsView,
    AnnouncementCreateView,
    AnnouncementReadView,
)
from api.views.auth_view import DevLoginView, LoginView, CustomTokenRefreshView
from api.views.bookings_view import (
    BookingCancelView,
    BookingCreateView,
    MyBookingsView,
    ResourceBlockView,
    ResourceScheduleView,
    ResourceUnblockView,
    BookingUpdateView,
    BookingDetailView,
)
from api.views.dictionaries_view import (
    FacultyListView,
    MajorListView,
    RoleListView,
    TargetTypeListView,
    DormitoryListView,
    FloorListView,
    RoomListView,
)
from api.views.locations_view import FloorsView, FloorMapDataView
from api.views.presence_view import PresenceCheckInView, PresenceGoHomeView
from api.views.socials_view import (
    FeedView,
    SocialEventCreateView,
    SocialEventDeleteView,
    SocialEventJoinView,
    SocialEventLeaveView,
    SocialSharingRequestCreateView,
    SocialSharingRequestDeleteView,
    SocialSharingRequestDoneView,
)
from api.views.user_view import UserDetailView

urlpatterns = [
    path("auth/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("floors/<int:dormitory_id>/", FloorsView.as_view(), name="floors"),
    path("floors/<int:floor_id>/map-data/", FloorMapDataView.as_view(), name="floor-map-data"),
    path("presence/check-in/", PresenceCheckInView.as_view(), name="presence-check-in"),
    path("presence/go-home/", PresenceGoHomeView.as_view(), name="presence-go-home"),
    path("feed/<int:page>/", FeedView.as_view(), name="feed"),
    path("events/", SocialEventCreateView.as_view(), name="event-create"),
    path("events/<int:event_id>/join/", SocialEventJoinView.as_view(), name="event-join"),
    path("events/<int:event_id>/leave/", SocialEventLeaveView.as_view(), name="event-leave"),
    path("events/<int:event_id>/", SocialEventDeleteView.as_view(), name="event-delete"),
    path("sharing-requests/", SocialSharingRequestCreateView.as_view(), name="sharing-request-create"),
    path(
        "sharing-requests/<int:request_id>/done/", SocialSharingRequestDoneView.as_view(), name="sharing-request-done"
    ),
    path("sharing-requests/<int:request_id>/", SocialSharingRequestDeleteView.as_view(), name="sharing-request-delete"),
    path("announcements/active/", ActiveAnnouncementsView.as_view(), name="announcements-active"),
    path("announcements/<int:announcement_id>/read/", AnnouncementReadView.as_view(), name="announcement-read"),
    path("announcements/", AnnouncementCreateView.as_view(), name="announcement-create"),
    path("resources/<int:resource_id>/schedule/", ResourceScheduleView.as_view(), name="resource-schedule"),
    path("resources/<int:resource_id>/block/", ResourceBlockView.as_view(), name="resource-block"),
    path("resources/<int:resource_id>/unblock/", ResourceUnblockView.as_view(), name="resource-unblock"),
    path("bookings/", BookingCreateView.as_view(), name="booking-create"),
    path("bookings/<int:booking_id>/", BookingUpdateView.as_view(), name="booking-update"),
    path("bookings/me/", MyBookingsView.as_view(), name="bookings-me"),
    path("bookings/<int:booking_id>/cancel/", BookingCancelView.as_view(), name="booking-cancel"),
    path("users/<uuid:user_id>/", UserDetailView.as_view(), name="user-info"),
    path("bookings/<int:booking_id>/", BookingDetailView.as_view(), name="booking-detail"),
    path("faculties/", FacultyListView.as_view(), name="faculty-list"),
    path("majors/", MajorListView.as_view(), name="major-list"),
    path("roles/", RoleListView.as_view(), name="role-list"),
    path("target-types/", TargetTypeListView.as_view(), name="target-type-list"),
    path("dormitories/", DormitoryListView.as_view(), name="dormitory-list"),
    path("floors/", FloorListView.as_view(), name="floor-list"),
    path("rooms/", RoomListView.as_view(), name="room-list"),
]

if settings.DEBUG:
    urlpatterns += [path("auth/dev-login/", DevLoginView.as_view(), name="dev_login")]
