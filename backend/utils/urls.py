from django.urls import re_path

from .views import ImageUploadAPI

urlpatterns = [
    # 관리자와 교사가 함께 쓴다. /api/admin/* 아래 두면 교사가 부를 수 없다.
    re_path(r"^image/?$", ImageUploadAPI.as_view(), name="image_upload_api"),
]
