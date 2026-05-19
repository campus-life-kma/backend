from django.conf import settings
from django.urls import path

from api.views.auth_view import DevLoginView, LoginView, CustomTokenRefreshView
from api.views.locations_view import FloorsView, FloorMapDataView

urlpatterns = [
    path("auth/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("floors/<int:dormitory_id>/", FloorsView.as_view(), name="floors"),
    path("floors/<int:floor_id>/map-data/", FloorMapDataView.as_view(), name="floor-map-data"),
]

if settings.DEBUG:
    urlpatterns += [path("auth/dev-login/", DevLoginView.as_view(), name="dev_login")]
