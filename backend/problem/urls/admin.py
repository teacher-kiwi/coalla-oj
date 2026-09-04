from django.urls import re_path

from ..views.admin import (ProblemAPI, TestCaseAPI, CompileSPJAPI, ContestProblemAPI,
                           ExportProblemAPI, ImportProblemAPI, ProblemPublishReviewAPI,
                           ProblemTagAdminAPI)

urlpatterns = [
    re_path(r"^test_case/?$", TestCaseAPI.as_view(), name="test_case_api"),
    re_path(r"^compile_spj/?$", CompileSPJAPI.as_view(), name="compile_spj"),
    re_path(r"^problem/tags/?$", ProblemTagAdminAPI.as_view(), name="problem_tag_admin_api"),
    re_path(r"^problem/publish_review/?$", ProblemPublishReviewAPI.as_view(),
            name="problem_publish_review_api"),
    re_path(r"^problem/?$", ProblemAPI.as_view(), name="problem_admin_api"),
    # 대회에 문제를 담고 뺀다. 문제를 복사하지 않으므로 "대회 문제 만들기" 는 없다.
    re_path(r"^contest/problem/?$", ContestProblemAPI.as_view(), name="contest_problem_admin_api"),
    re_path(r"^export_problem/?$", ExportProblemAPI.as_view(), name="export_problem_api"),
    re_path(r"^import_problem/?$", ImportProblemAPI.as_view(), name="import_problem_api"),
]
