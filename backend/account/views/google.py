"""구글 로그인과 교사 가입 신청.

교사는 구글 계정으로 로그인하고, 최고관리자 승인을 받아야 교사 권한을 얻는다.
학생은 교사가 만들어준 아이디/비밀번호로 로그인하므로 이 경로를 쓰지 않는다.
"""
import logging

from django.contrib import auth
from django.utils.timezone import now

from options.options import SysOptions
from utils.api import APIView, validate_serializer
from utils.shortcuts import rand_str
from ..decorators import login_required, super_admin_required
from ..models import (AdminType, ProblemPermission, TeacherApplication,
                      TeacherApplicationStatus, User, UserProfile)
from ..serializers import (GoogleLoginSerializer, ReviewTeacherApplicationSerializer,
                           TeacherApplicationSerializer)

logger = logging.getLogger(__name__)


def _unique_username(base):
    """구글 이메일 앞부분으로 아이디를 만들되, 중복이면 접미사를 붙인다."""
    base = "".join(c for c in (base or "").lower() if c.isalnum() or c in "._-")[:24] or "teacher"
    candidate = base
    while User.objects.filter(username=candidate).exists():
        candidate = f"{base}-{rand_str(4)}"
    return candidate


def verify_google_token(credential, client_id):
    """구글 ID 토큰을 검증해 claims 를 돌려준다. 실패하면 None.

    지연 임포트를 쓰는 이유: 구글 로그인을 쓰지 않는 배포에서도 서버가 뜨도록.
    테스트에서는 이 함수를 대체한다.
    """
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token
    except ImportError:
        logger.error("google-auth 패키지가 설치되지 않았습니다")
        return None
    try:
        return google_id_token.verify_oauth2_token(
            credential, google_requests.Request(), client_id)
    except ValueError as e:
        logger.warning(f"구글 ID 토큰 검증 실패: {e}")
        return None


class GoogleLoginAPI(APIView):
    @validate_serializer(GoogleLoginSerializer)
    def post(self, request):
        client_id = SysOptions.google_client_id
        if not client_id:
            return self.error("구글 로그인이 설정되지 않았습니다. 관리자에게 문의하세요")

        claims = verify_google_token(request.data["credential"], client_id)
        if not claims:
            return self.error("구글 인증에 실패했습니다. 다시 시도해주세요")

        if not claims.get("email_verified"):
            return self.error("이메일 인증이 완료되지 않은 구글 계정입니다")

        sub, email = claims["sub"], claims.get("email", "").lower()
        user = User.objects.filter(google_sub=sub).first()

        if user is None:
            # 같은 이메일로 만들어 둔 기존 계정이 있으면 구글 계정을 연결한다.
            user = User.objects.filter(email=email).first() if email else None
            if user is not None:
                user.google_sub = sub
                user.save(update_fields=["google_sub"])
            else:
                user = User.objects.create(
                    username=_unique_username(email.split("@")[0] if email else ""),
                    email=email or None,
                    google_sub=sub,
                    admin_type=AdminType.REGULAR_USER)
                user.set_unusable_password()
                user.save()
                UserProfile.objects.create(user=user, real_name=claims.get("name") or None)

        if user.is_disabled:
            return self.error("비활성화된 계정입니다")

        # 이미 권한이 있는 사용자(교사·관리자)는 바로 로그인
        if user.is_teacher() or user.is_admin_role():
            auth.login(request, user)
            return self.success({"status": "logged_in"})

        application, _ = TeacherApplication.objects.get_or_create(user=user)
        if application.status == TeacherApplicationStatus.REJECTED:
            return self.error("교사 가입 신청이 반려되었습니다. 관리자에게 문의하세요")
        # 승인 대기: 로그인시키지 않는다.
        return self.success({"status": "pending"})


class TeacherApplicationAPI(APIView):
    @login_required
    def get(self, request):
        """내 신청 상태 조회"""
        application = TeacherApplication.objects.filter(user=request.user).first()
        if not application:
            return self.success(None)
        return self.success(TeacherApplicationSerializer(application).data)


class TeacherApplicationAdminAPI(APIView):
    @super_admin_required
    def get(self, request):
        applications = TeacherApplication.objects.select_related("user", "reviewed_by")
        status = request.GET.get("status")
        if status:
            applications = applications.filter(status=status)
        return self.success(self.paginate_data(request, applications, TeacherApplicationSerializer))

    @validate_serializer(ReviewTeacherApplicationSerializer)
    @super_admin_required
    def put(self, request):
        data = request.data
        try:
            application = TeacherApplication.objects.select_related("user").get(id=data["id"])
        except TeacherApplication.DoesNotExist:
            return self.error("신청 내역이 존재하지 않습니다")
        if application.status != TeacherApplicationStatus.PENDING:
            return self.error("이미 처리된 신청입니다")

        application.status = data["status"]
        application.note = data.get("note", "")
        application.reviewed_at = now()
        application.reviewed_by = request.user
        application.save()

        if data["status"] == TeacherApplicationStatus.APPROVED:
            user = application.user
            user.admin_type = AdminType.TEACHER
            user.problem_permission = ProblemPermission.OWN
            user.save(update_fields=["admin_type", "problem_permission"])

        return self.success(TeacherApplicationSerializer(application).data)
