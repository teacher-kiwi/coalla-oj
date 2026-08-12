from django.urls import re_path

from ..views.student import (StudentChangePasswordAPI, StudentClassSearchAPI,
                             StudentLoginAPI, StudentSchoolSearchAPI)

urlpatterns = [
    re_path(r"^school/?$", StudentSchoolSearchAPI.as_view(), name="student_school_search_api"),
    re_path(r"^class/?$", StudentClassSearchAPI.as_view(), name="student_class_search_api"),
    re_path(r"^login/?$", StudentLoginAPI.as_view(), name="student_login_api"),
    re_path(r"^change_password/?$", StudentChangePasswordAPI.as_view(),
            name="student_change_password_api"),
]
