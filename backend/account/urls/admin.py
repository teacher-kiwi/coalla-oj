from django.urls import re_path

from ..views.admin import UserAdminAPI, GenerateUserAPI
from ..views.google import SchoolSyncAPI, TeacherApplicationAdminAPI

urlpatterns = [
    re_path(r"^user/?$", UserAdminAPI.as_view(), name="user_admin_api"),
    re_path(r"^generate_user/?$", GenerateUserAPI.as_view(), name="generate_user_api"),
    re_path(r"^teacher_application/?$", TeacherApplicationAdminAPI.as_view(), name="teacher_application_admin_api"),
    re_path(r"^school_sync/?$", SchoolSyncAPI.as_view(), name="school_sync_api"),
]
