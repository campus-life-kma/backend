from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection

from api.models import User


class AnnouncementEmailService:
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
        users = User.objects.filter(is_activated=True).exclude(email="")
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
