import logging
from threading import Thread

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.db import close_old_connections

from api.models import Announcement, User

logger = logging.getLogger(__name__)


class AnnouncementEmailService:
    def send_announcement_async(self, announcement_id):
        thread = Thread(target=self.send_announcement_by_id, args=(announcement_id,), daemon=True)
        thread.start()
        return thread

    def send_announcement_by_id(self, announcement_id):
        close_old_connections()
        try:
            announcement = (
                Announcement.objects.select_related("target_type", "target_floor", "target_room")
                .prefetch_related("target_users")
                .get(id=announcement_id)
            )
            return self.send_announcement(announcement)
        except Exception:
            logger.exception("Не вдалося надіслати email-сповіщення для оголошення %s.", announcement_id)
            return 0
        finally:
            close_old_connections()

    def send_announcement(self, announcement):
        recipients = list(self.get_recipients(announcement))
        if not recipients:
            return 0

        subject = f"Campus Life: {announcement.title}"
        recipient_emails = [user.email for user in recipients]
        message = EmailMultiAlternatives(
            subject=subject,
            body=self.build_body(announcement),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_emails,
        )

        connection = get_connection(fail_silently=False)
        return connection.send_messages([message])

    def get_recipients(self, announcement):
        users = User.objects.filter(is_active=True, is_activated=True).exclude(email="")
        target_type = announcement.target_type.type

        if target_type == "GLOBAL":
            return users.distinct()

        if target_type == "FLOOR":
            return users.filter(room__floor=announcement.target_floor).distinct()

        if target_type == "ROOM":
            return users.filter(room=announcement.target_room).distinct()

        if target_type == "SPECIFIC_USERS":
            return users.filter(targeted_announcements=announcement).distinct()

        return User.objects.none()

    def build_body(self, announcement):
        return (
            "Вітаємо!\n\n"
            f"{announcement.message}\n\n"
            "Це оголошення надіслано через систему Campus Life.\n"
            "Якщо воно більше не актуальне для вас, відкрийте додаток і натисніть «Зрозуміло»."
        )
