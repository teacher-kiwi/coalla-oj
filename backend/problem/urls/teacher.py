from django.urls import re_path

from ..views.teacher import (ProblemSetAPI, ProblemSetAssignmentAPI, ProblemSetProblemAPI,
                             ProblemSetProgressAPI, TeacherProblemAPI,
                             TeacherProblemPublishAPI, TeacherTestCaseAPI)

urlpatterns = [
    re_path(r"^problem_set/?$", ProblemSetAPI.as_view(), name="teacher_problem_set_api"),
    re_path(r"^problem_set/problem/?$", ProblemSetProblemAPI.as_view(),
            name="teacher_problem_set_problem_api"),
    re_path(r"^problem_set/assignment/?$", ProblemSetAssignmentAPI.as_view(),
            name="teacher_problem_set_assignment_api"),
    re_path(r"^problem_set/progress/?$", ProblemSetProgressAPI.as_view(),
            name="teacher_problem_set_progress_api"),
    re_path(r"^problem/test_case/?$", TeacherTestCaseAPI.as_view(),
            name="teacher_test_case_api"),
    re_path(r"^problem/?$", TeacherProblemAPI.as_view(), name="teacher_problem_api"),
    re_path(r"^problem/publish/?$", TeacherProblemPublishAPI.as_view(),
            name="teacher_problem_publish_api"),
]
