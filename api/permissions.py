from rest_framework import permissions

from api.models import User


class AdminPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if isinstance(user, User) and user.is_authenticated:
            return user.is_admin
        return False


class ModeratorPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if isinstance(user, User) and user.is_authenticated:
            return user.is_moderator
        return False


class AuthenticatedPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
