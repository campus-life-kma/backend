from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection

from api.models import User


class AnnouncementEmailService:
    """Сервіс для розсилання оголошень електронною поштою відповідним користувачам."""

    def send_announcement(self, announcement) -> int:
        """Надсилає оголошення списку отримувачів електронною поштою.

        Args:
            announcement: Об'єкт оголошення (Announcement), яке потрібно надіслати.

        Returns:
            int: Кількість успішно надісланих повідомлень.
        """
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

        # Використовуємо стандартне з'єднання Django для відправки пошти
        connection = get_connection(fail_silently=False)
        return connection.send_messages([message])

    def get_recipients(self, announcement):
        """Визначає список користувачів-отримувачів залежно від типу цілі оголошення.

        Args:
            announcement: Об'єкт оголошення (Announcement).

        Returns:
            QuerySet: Список користувачів, які підходять під критерії оголошення.
        """
        users = User.objects.filter(is_activated=True).exclude(email="")
        target_type = announcement.target_type.type

        # Глобальне оголошення — надсилається всім активованим користувачам
        if target_type == "GLOBAL":
            return users.distinct()

        # На рівні поверху — надсилається мешканцям кімнат на вказаному поверсі
        if target_type == "FLOOR":
            return users.filter(room__floor=announcement.target_floor).distinct()

        # На рівні конкретної кімнати — надсилається мешканцям цієї кімнати
        if target_type == "ROOM":
            return users.filter(room=announcement.target_room).distinct()

        # Для конкретного списку користувачів
        if target_type == "SPECIFIC_USERS":
            return users.filter(targeted_announcements=announcement).distinct()

        return User.objects.none()

    def build_body(self, announcement) -> str:
        """Формує текстовий вміст листа оголошення.

        Args:
            announcement: Об'єкт оголошення (Announcement).

        Returns:
            str: Сформований текст листа.
        """
        return (
            "Вітаємо!\n\n"
            f"{announcement.message}\n\n"
            "Це оголошення надіслано через систему Campus Life.\n"
            "Якщо воно більше не актуальне для вас, відкрийте додаток і натисніть «Зрозуміло»."
        )
