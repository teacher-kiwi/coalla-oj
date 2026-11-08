from django.urls import re_path

from ..views.teacher import (TeacherHomeworkAPI, TeacherHomeworkBoardAPI,
                             TeacherHomeworkParticipantAPI, TeacherHomeworkSubmissionAPI)

urlpatterns = [
    re_path(r"^hw/?$", TeacherHomeworkAPI.as_view(), name="teacher_homework_api"),
    re_path(r"^hw/board/?$", TeacherHomeworkBoardAPI.as_view(), name="teacher_homework_board_api"),
    re_path(r"^hw/submission/?$", TeacherHomeworkSubmissionAPI.as_view(),
            name="teacher_homework_submission_api"),
    re_path(r"^hw/participant/?$", TeacherHomeworkParticipantAPI.as_view(),
            name="teacher_homework_participant_api"),
]
