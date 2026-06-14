from rest_framework import permissions

from api.models import User


class AdminPermission(permissions.BasePermission):
    """Дозвіл, що надає доступ виключно користувачам із роллю адміністратора."""

    def has_permission(self, request, view) -> bool:
        """Перевіряє, чи є користувач адміністратором.

        Args:
            request: Об'єкт HTTP-запиту.
            view: Об'єкт представлення (DRF View).

        Returns:
            bool: True, якщо користувач авторизований та є адміністратором.
        """
        user = request.user
        if isinstance(user, User) and user.is_authenticated:
            return user.is_admin
        return False


class ModeratorPermission(permissions.BasePermission):
    """Дозвіл, що надає доступ користувачам із роллю модератора поверху або адміністратора."""

    def has_permission(self, request, view) -> bool:
        """Перевіряє, чи є користувач модератором.

        Args:
            request: Об'єкт HTTP-запиту.
            view: Об'єкт представлення.

        Returns:
            bool: True, якщо користувач авторизований та є модератором.
        """
        user = request.user
        if isinstance(user, User) and user.is_authenticated:
            return user.is_moderator
        return False


class AuthenticatedPermission(permissions.BasePermission):
    """Дозвіл, що вимагає обов'язкову авторизацію будь-якого користувача."""

    def has_permission(self, request, view) -> bool:
        """Перевіряє, чи авторизований користувач.

        Args:
            request: Об'єкт HTTP-запиту.
            view: Об'єкт представлення.

        Returns:
            bool: True, якщо користувач пройшов авторизацію.
        """
        return bool(request.user and request.user.is_authenticated)
