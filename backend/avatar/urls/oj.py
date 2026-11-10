from django.urls import re_path

from ..views.oj import CoinLogAPI

urlpatterns = [
    re_path(r"^coin_log/?$", CoinLogAPI.as_view(), name="coin_log_api"),
]
