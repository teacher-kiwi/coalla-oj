from django.urls import re_path

from ..views.teacher import (SchoolClassAPI, SchoolListAPI, StudentAPI, StudentSheetAPI,
                             StudentSubmissionAPI)

urlpatterns = [
    re_path(r"^school/?$", SchoolListAPI.as_view(), name="teacher_school_api"),
    re_path(r"^class/?$", SchoolClassAPI.as_view(), name="teacher_class_api"),
    re_path(r"^student/?$", StudentAPI.as_view(), name="teacher_student_api"),
    re_path(r"^student/sheet/?$", StudentSheetAPI.as_view(), name="teacher_student_sheet_api"),
    re_path(r"^student/submission/?$", StudentSubmissionAPI.as_view(),
            name="teacher_student_submission_api"),
]
