from django.urls import re_path

from ..views.teacher import (ProblemSetAPI, ProblemSetAssignmentAPI, ProblemSetProblemAPI)

urlpatterns = [
    re_path(r"^problem_set/?$", ProblemSetAPI.as_view(), name="teacher_problem_set_api"),
    re_path(r"^problem_set/problem/?$", ProblemSetProblemAPI.as_view(),
            name="teacher_problem_set_problem_api"),
    re_path(r"^problem_set/assignment/?$", ProblemSetAssignmentAPI.as_view(),
            name="teacher_problem_set_assignment_api"),
]
