import logging
import mimetypes
from datetime import date

import requests
from django.core.files.base import ContentFile
from rest_framework_simplejwt.tokens import RefreshToken

from api.dtos.auth_dtos import MicrosoftUserDTO
from api.models import User, Major
from api.serializers.user_serializer import UserBaseSerializer

logger = logging.getLogger(__name__)


class DevLoginService:
    def execute_login(self, email: str) -> dict | None:
        try:
            user = User.objects.get(email=email, is_activated=True)
            refresh = RefreshToken.for_user(user)

            return {"access": str(refresh.access_token), "refresh": str(refresh), "user": UserBaseSerializer(user).data}
        except User.DoesNotExist:
            return None


class LoginService:
    GRAPH_API_URL = "https://graph.microsoft.com/v1.0/me"
    PHOTO_API_URL = "https://graph.microsoft.com/v1.0/me/photo/$value"

    def _activate_user(self, user: User, dto: MicrosoftUserDTO, headers: dict) -> None:
        names_changed = self._update_user_names(user, dto)
        academic_changed = self._update_user_academic_info(user, dto)
        photo_changed = self._update_user_photo(user, headers)

        if names_changed or academic_changed or photo_changed:
            user.save()

        user.is_activated = True

    def _update_user_names(self, user: User, dto: MicrosoftUserDTO) -> bool:
        user_changed = False
        surname, name, middle_name = dto.get_parsed_name()

        if not user.surname and surname:
            user.surname = surname
            user_changed = True
        elif not surname:
            logger.info("User surname not found in microsoft database!")

        if not user.name and name:
            user.name = name
            user_changed = True
        elif not name:
            logger.info("User name not found in microsoft database!")

        if not user.middle_name and middle_name:
            user.middle_name = middle_name
            user_changed = True
        elif not middle_name:
            logger.info("User middle name not found in microsoft database!")

        return user_changed

    def _update_user_academic_info(self, user: User, dto: MicrosoftUserDTO) -> bool:
        user_changed = False
        major_name, admission_year = dto.get_parsed_academic_info()

        if not admission_year:
            logger.info("Admission year not found in microsoft database!")
        elif not user.year:
            today = date.today()
            calc_year = today.year - admission_year + (1 if today.month >= 8 else 0)
            user.year = max(1, min(calc_year, 4))
            user_changed = True

        if not major_name:
            logger.info("Major not found in microsoft database!")
        elif not user.major:
            major = Major.objects.filter(name__icontains=major_name).first()
            if major:
                user.major = major
                user_changed = True
            else:
                logger.warning(f"Major {major_name} not found in database!")

        return user_changed

    def _update_user_photo(self, user: User, headers: dict) -> bool:
        if user.photo:
            return False

        try:
            photo_res = requests.get(self.PHOTO_API_URL, headers=headers, timeout=5)
            if photo_res.status_code == 200:
                content_type = photo_res.headers.get("Content-Type", "image/jpeg")
                extension = mimetypes.guess_extension(content_type) or ".jpg"
                file_name = f"avatar_{user.id}{extension}"
                user.photo.save(file_name, ContentFile(photo_res.content), save=False)
                return True
            else:
                logger.info(
                    f"Photo not found or API error. Status: {photo_res.status_code}, " f"Details: {photo_res.text}"
                )
        except requests.exceptions.RequestException as e:
            logger.warning(f"Photo API Connection Error: {e}")

        return False

    def execute_login(self, microsoft_access_token: str) -> dict | None:
        headers = {"Authorization": f"Bearer {microsoft_access_token}", "Content-Type": "application/json"}

        try:
            params = {"$select": "userPrincipalName,mail,displayName,jobTitle"}
            res = requests.get(self.GRAPH_API_URL, headers=headers, params=params, timeout=10)

            if res.status_code != 200:
                logger.warning(f"Graph API Error: {res.status_code}, Details: {res.text}")
                return None

            json_data = res.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Graph API Connection Error: {e}")
            return None

        dto = MicrosoftUserDTO.from_json(json_data)

        if not dto.is_valid_email:
            return None

        try:
            user = User.objects.get(email=dto.email)
        except User.DoesNotExist:
            return None

        if not user.is_activated:
            self._activate_user(user, dto, headers)

        refresh = RefreshToken.for_user(user)
        return {"access": str(refresh.access_token), "refresh": str(refresh), "user": UserBaseSerializer(user).data}
