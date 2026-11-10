from django.urls import re_path

from ..views.oj import BuyAPI, CoinLogAPI, EquipAPI, LooksAPI, ShopAPI

urlpatterns = [
    re_path(r"^coin_log/?$", CoinLogAPI.as_view(), name="coin_log_api"),
    re_path(r"^avatar/shop/?$", ShopAPI.as_view(), name="avatar_shop_api"),
    re_path(r"^avatar/buy/?$", BuyAPI.as_view(), name="avatar_buy_api"),
    re_path(r"^avatar/equip/?$", EquipAPI.as_view(), name="avatar_equip_api"),
    re_path(r"^avatar/looks/?$", LooksAPI.as_view(), name="avatar_looks_api"),
]
