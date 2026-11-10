from django.urls import re_path

from ..views.admin import AvatarItemAdminAPI

urlpatterns = [
    re_path(r"^avatar_item/?$", AvatarItemAdminAPI.as_view(), name="avatar_item_admin_api"),
]
