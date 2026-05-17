from django.conf import settings
from django.urls import path

from api.views.auth_view import DevLoginView, LoginView, CustomTokenRefreshView

urlpatterns = [
    path("auth/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("auth/login/", LoginView.as_view(), name="login"),
]

if settings.DEBUG:
    urlpatterns += [path("auth/dev-login/", DevLoginView.as_view(), name="dev_login")]
