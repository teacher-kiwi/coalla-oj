from django.urls import include, re_path

urlpatterns = [
    re_path(r"^api/", include("account.urls.oj")),
    re_path(r"^api/admin/", include("account.urls.admin")),
    # 교사 전용. /api/admin/* 과 분리해 미들웨어의 admin_role 검사를 타지 않는다.
    re_path(r"^api/teacher/", include("account.urls.teacher")),
    re_path(r"^api/student/", include("account.urls.student")),
    re_path(r"^api/", include("announcement.urls.oj")),
    re_path(r"^api/admin/", include("announcement.urls.admin")),
    re_path(r"^api/", include("conf.urls.oj")),
    re_path(r"^api/admin/", include("conf.urls.admin")),
    re_path(r"^api/", include("problem.urls.oj")),
    re_path(r"^api/admin/", include("problem.urls.admin")),
    re_path(r"^api/", include("contest.urls.oj")),
    re_path(r"^api/admin/", include("contest.urls.admin")),
    re_path(r"^api/", include("submission.urls.oj")),
    re_path(r"^api/admin/", include("submission.urls.admin")),
    re_path(r"^api/admin/", include("utils.urls")),
]
