from django.conf import settings
from django.urls import path

from api.views.announcements_view import (
    ActiveAnnouncementsView,
    AnnouncementCreateView,
    AnnouncementRecipientsView,
    AnnouncementReadView,
)
from api.views.auth_view import AuthMeView, DevLoginView, LoginView, CustomTokenRefreshView
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
    RoomTypeListView,
    ResourceTypeListView,
)
from api.views.locations_view import (
    FloorsView,
    FloorMapDataView,
    RoomBlockView,
    RoomUnblockView,
    RoomUpdateView,
    ResourceCreateView,
    ResourceDetailView,
)
from api.views.presence_view import PresenceCheckInView, PresenceGoHomeView, PresenceMeView
from api.views.socials_view import (
    FeedView,
    SocialEventCreateView,
    SocialEventJoinView,
    SocialEventLeaveView,
    SocialSharingRequestCreateView,
    SocialSharingRequestDoneView,
    SocialSharingRequestDetailView,
    UserSocialProfileView,
    SocialEventDetailView,
)
from api.views.statistics_view import StatisticsSummaryView
from api.views.user_view import UserDetailView

urlpatterns = [
    path("auth/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/me/", AuthMeView.as_view(), name="auth-me"),
    path("floors/<int:dormitory_id>/", FloorsView.as_view(), name="floors"),
    path("floors/<int:floor_id>/map-data/", FloorMapDataView.as_view(), name="floor-map-data"),
    path("rooms/<int:room_id>/block/", RoomBlockView.as_view(), name="room-block"),
    path("rooms/<int:room_id>/unblock/", RoomUnblockView.as_view(), name="room-unblock"),
    path("presence/me/", PresenceMeView.as_view(), name="presence-me"),
    path("presence/check-in/", PresenceCheckInView.as_view(), name="presence-check-in"),
    path("presence/go-home/", PresenceGoHomeView.as_view(), name="presence-go-home"),
    path("feed/<int:page>/", FeedView.as_view(), name="feed"),
    path("events/", SocialEventCreateView.as_view(), name="event-create"),
    path("events/<int:event_id>/join/", SocialEventJoinView.as_view(), name="event-join"),
    path("events/<int:event_id>/leave/", SocialEventLeaveView.as_view(), name="event-leave"),
    path("events/<int:event_id>/", SocialEventDetailView.as_view(), name="event-detail"),
    path("sharing-requests/", SocialSharingRequestCreateView.as_view(), name="sharing-request-create"),
    path(
        "sharing-requests/<int:request_id>/done/", SocialSharingRequestDoneView.as_view(), name="sharing-request-done"
    ),
    path("sharing-requests/<int:request_id>/", SocialSharingRequestDetailView.as_view(), name="sharing-request-detail"),
    path("announcements/active/", ActiveAnnouncementsView.as_view(), name="announcements-active"),
    path("announcements/recipients/", AnnouncementRecipientsView.as_view(), name="announcement-recipients"),
    path("announcements/<int:announcement_id>/read/", AnnouncementReadView.as_view(), name="announcement-read"),
    path("announcements/", AnnouncementCreateView.as_view(), name="announcement-create"),
    path("statistics/summary/", StatisticsSummaryView.as_view(), name="statistics-summary"),
    path("resources/<int:resource_id>/schedule/", ResourceScheduleView.as_view(), name="resource-schedule"),
    path("resources/<int:resource_id>/block/", ResourceBlockView.as_view(), name="resource-block"),
    path("resources/<int:resource_id>/unblock/", ResourceUnblockView.as_view(), name="resource-unblock"),
    path("bookings/", BookingCreateView.as_view(), name="booking-create"),
    path("bookings/<int:booking_id>/", BookingUpdateView.as_view(), name="booking-update"),
    path("bookings/me/", MyBookingsView.as_view(), name="bookings-me"),
    path("bookings/<int:booking_id>/cancel/", BookingCancelView.as_view(), name="booking-cancel"),
    path("users/<uuid:user_id>/", UserDetailView.as_view(), name="user-info"),
    path("users/<uuid:user_id>/social-activity/", UserSocialProfileView.as_view(), name="user-social-activity"),
    path("bookings/<int:booking_id>/", BookingDetailView.as_view(), name="booking-detail"),
    path("faculties/", FacultyListView.as_view(), name="faculty-list"),
    path("majors/", MajorListView.as_view(), name="major-list"),
    path("roles/", RoleListView.as_view(), name="role-list"),
    path("target-types/", TargetTypeListView.as_view(), name="target-type-list"),
    path("dormitories/", DormitoryListView.as_view(), name="dormitory-list"),
    path("floors/", FloorListView.as_view(), name="floor-list"),
    path("rooms/", RoomListView.as_view(), name="room-list"),
    path("room-types/", RoomTypeListView.as_view(), name="room-type-list"),
    path("resource-types/", ResourceTypeListView.as_view(), name="resource-type-list"),
    path("rooms/<int:room_id>/", RoomUpdateView.as_view(), name="room-update"),
    path("rooms/<int:room_id>/resources/", ResourceCreateView.as_view(), name="resource-create"),
    path("resources/<int:resource_id>/", ResourceDetailView.as_view(), name="resource-detail"),
]

if settings.DEBUG:
    urlpatterns += [path("auth/dev-login/", DevLoginView.as_view(), name="dev_login")]
