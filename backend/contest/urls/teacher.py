from django.urls import re_path

from ..views.teacher import (TeacherContestAnnouncementAPI, TeacherContestAPI,
                             TeacherContestAssignmentAPI, TeacherContestProblemAPI)

urlpatterns = [
    re_path(r"^contest/?$", TeacherContestAPI.as_view(), name="teacher_contest_api"),
    re_path(r"^contest/class/?$", TeacherContestAssignmentAPI.as_view(),
            name="teacher_contest_class_api"),
    re_path(r"^contest/problem/?$", TeacherContestProblemAPI.as_view(),
            name="teacher_contest_problem_api"),
    re_path(r"^contest/announcement/?$", TeacherContestAnnouncementAPI.as_view(),
            name="teacher_contest_announcement_api"),
]
