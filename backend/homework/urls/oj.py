from django.urls import re_path

from ..views.oj import (HomeworkAPI, HomeworkJoinAPI, HomeworkMeAPI, HomeworkProblemAPI,
                        HomeworkRunAPI, HomeworkSubmissionAPI)

# 코드는 6자리 숫자다. 쿠키 경로(/api/hw/<코드>)가 이 아래를 모두 덮어야 한다.
urlpatterns = [
    re_path(r"^(?P<code>\d{6})/?$", HomeworkAPI.as_view(), name="homework_api"),
    re_path(r"^(?P<code>\d{6})/join/?$", HomeworkJoinAPI.as_view(), name="homework_join_api"),
    re_path(r"^(?P<code>\d{6})/me/?$", HomeworkMeAPI.as_view(), name="homework_me_api"),
    re_path(r"^(?P<code>\d{6})/problem/?$", HomeworkProblemAPI.as_view(),
            name="homework_problem_api"),
    re_path(r"^(?P<code>\d{6})/submission/?$", HomeworkSubmissionAPI.as_view(),
            name="homework_submission_api"),
    re_path(r"^(?P<code>\d{6})/run/?$", HomeworkRunAPI.as_view(), name="homework_run_api"),
]
