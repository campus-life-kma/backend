from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from api.models import User
from api.serializers.user_serializer import AdminUserUpdateSerializer, UserUpdateSerializer


class UserService:
    def get_user_by_id(self, user_id: str) -> User:
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise NotFound(detail="Користувача з таким id не знайдено!")

    def update_profile(self, acting_user: User, target_user_id: str, update_data: dict) -> User:
        target_user = UserService.get_user_by_id(self, target_user_id)

        if not acting_user.is_admin and acting_user.id != target_user.id:
            raise PermissionDenied(detail="Ви не маєте прав для редагування цього профілю.")

        if acting_user.is_admin:
            serializer_class = AdminUserUpdateSerializer
        else:
            serializer_class = UserUpdateSerializer

        serializer = serializer_class(target_user, data=update_data, partial=True)

        if not serializer.is_valid():
            raise ValidationError(serializer.errors)

        return serializer.save()
