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
    """Налаштування панелі адміністратора для моделі User."""

    list_display = ("email", "full_name", "major", "year", "is_activated")
    list_filter = ("is_activated", "year", "role", "is_staff")
    search_fields = ("email", "full_name")
    ordering = ("email",)


@admin.register(Dormitory)
class DormitoryAdmin(admin.ModelAdmin):
    """Налаштування панелі адміністратора для моделі Dormitory."""

    list_display = ("name", "location")


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    """Налаштування панелі адміністратора для моделі Floor."""

    list_display = ("dormitory", "number", "notice")
    list_filter = ("dormitory",)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    """Налаштування панелі адміністратора для моделі Room."""

    list_display = ("name", "floor", "room_type", "max_person", "is_blocked")
    list_filter = ("room_type", "is_blocked", "floor__dormitory")
    search_fields = ("name",)


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    """Налаштування панелі адміністратора для моделі Resource."""

    list_display = ("name", "room", "is_blocked")


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    """Налаштування панелі адміністратора для моделі Faculty."""

    search_fields = ("name",)


@admin.register(Major)
class MajorAdmin(admin.ModelAdmin):
    """Налаштування панелі адміністратора для моделі Major."""

    list_display = ("name", "faculty")
    list_filter = ("faculty",)


@admin.register(Presence)
class PresenceAdmin(admin.ModelAdmin):
    """Налаштування панелі адміністратора для моделі Presence."""

    list_display = ("user", "room", "joined_at", "expires_at")
    list_filter = ("room",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """Налаштування панелі адміністратора для моделі Booking."""

    list_display = ("resource", "user", "start_time", "end_time", "status")
    list_filter = ("status", "start_time")


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    """Налаштування панелі адміністратора для моделі Announcement."""

    list_display = ("title", "target_type", "creator", "created_at", "is_pinned")
    list_filter = ("target_type", "is_pinned", "created_at")
    search_fields = ("title", "message")


@admin.register(SocialEvent)
class SocialEventAdmin(admin.ModelAdmin):
    """Налаштування панелі адміністратора для моделі SocialEvent."""

    list_display = ("title", "creator", "start_time", "max_person")
    list_filter = ("start_time", "is_faculty_only")


# Реєстрація простих моделей та словникових таблиць
admin.site.register(Role)
admin.site.register(RoomType)
admin.site.register(BookingStatus)
admin.site.register(TargetType)
admin.site.register(AnnouncementRead)
admin.site.register(SocialSharingStatus)
admin.site.register(SocialSharingRequest)
