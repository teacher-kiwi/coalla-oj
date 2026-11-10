from django.conf import settings
from django.db import connection
from django.utils.timezone import now
from django.utils.deprecation import MiddlewareMixin

from utils.api import JSONResponse


class SessionRecordMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.ip = request.META.get(settings.IP_HEADER, request.META.get("REMOTE_ADDR"))
        if request.user.is_authenticated:
            session = request.session
            session["user_agent"] = request.META.get("HTTP_USER_AGENT", "")
            session["ip"] = request.ip
            session["last_activity"] = now()
            user_sessions = request.user.session_keys
            if session.session_key not in user_sessions:
                user_sessions.append(session.session_key)
                request.user.save()


CONTEST_ADMIN_PATHS = ("/api/admin/contest", "/api/admin/download_submissions")


class AdminRoleRequiredMiddleware(MiddlewareMixin):
    def process_request(self, request):
        path = request.path_info
        if path.startswith("/admin/") or path.startswith("/api/admin/"):
            if not (request.user.is_authenticated and request.user.is_admin_role()):
                return JSONResponse.response({"error": "login-required", "data": "먼저 로그인하세요"})
            # 대회 관리(대회·대회 공지·대회 문제·제출 내려받기)는 대회 권한이 있어야 한다.
            # 뷰마다 데코레이터를 다는 대신 주소로 한곳에서 막는다.
            if path.startswith(CONTEST_ADMIN_PATHS) and not request.user.can_manage_contest():
                return JSONResponse.response({"error": "permission-denied", "data": "대회 권한이 없습니다"})


class LogSqlMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        print("\033[94m", "#" * 30, "\033[0m")
        time_threshold = 0.03
        for query in connection.queries:
            if float(query["time"]) > time_threshold:
                print("\033[93m", query, "\n", "-" * 30, "\033[0m")
            else:
                print(query, "\n", "-" * 30)
        return response
