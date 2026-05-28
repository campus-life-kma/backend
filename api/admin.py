from django.contrib import admin

from .models import (
    User,
    Role,
    Faculty,
    Major,
    Dormitory,
    Floor,
    RoomType,
    Room,
    Resource,
    Presence,
    BookingStatus,
    Booking,
    TargetType,
    Announcement,
    AnnouncementRead,
    SocialEvent,
    SocialSharingStatus,
    SocialSharingRequest,
)


@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "major", "year", "is_activated")
    list_filter = ("is_activated", "year", "role", "is_staff")
    search_fields = ("email", "full_name")
    ordering = ("email",)


@admin.register(Dormitory)
class DormitoryAdmin(admin.ModelAdmin):
    list_display = ("name", "location")


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    list_display = ("dormitory", "number")
    list_filter = ("dormitory",)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "floor", "room_type", "max_person", "is_blocked")
    list_filter = ("room_type", "is_blocked", "floor__dormitory")
    search_fields = ("name",)


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("name", "room", "is_blocked")


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Major)
class MajorAdmin(admin.ModelAdmin):
    list_display = ("name", "faculty")
    list_filter = ("faculty",)


@admin.register(Presence)
class PresenceAdmin(admin.ModelAdmin):
    list_display = ("user", "room", "joined_at", "expires_at")
    list_filter = ("room",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("resource", "user", "start_time", "end_time", "status")
    list_filter = ("status", "start_time")


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "target_type", "creator", "created_at", "is_pinned")
    list_filter = ("target_type", "is_pinned", "created_at")
    search_fields = ("title", "message")


@admin.register(SocialEvent)
class SocialEventAdmin(admin.ModelAdmin):
    list_display = ("title", "creator", "start_time", "max_person")
    list_filter = ("start_time", "is_faculty_only")


admin.site.register(Role)
admin.site.register(RoomType)
admin.site.register(BookingStatus)
admin.site.register(TargetType)
admin.site.register(AnnouncementRead)
admin.site.register(SocialSharingStatus)
admin.site.register(SocialSharingRequest)
