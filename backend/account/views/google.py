"""구글 로그인과 교사 가입 신청.

교사는 구글 계정으로 로그인하고, 최고관리자 승인을 받아야 교사 권한을 얻는다.
학생은 교사가 만들어준 아이디/비밀번호로 로그인하므로 이 경로를 쓰지 않는다.
"""
import logging
import re

from django.contrib import auth
from django.db import transaction
from django.utils.timezone import now

from options.options import SysOptions
from utils.api import APIView, validate_serializer
from ..decorators import login_required, super_admin_required
from ..models import (AdminType, ProblemPermission,
                      RESERVED_USERNAME_PREFIX_MESSAGE,
                      TeacherApplication, TeacherApplicationStatus,
                      User, UserProfile, is_reserved_username)
from ..teaching import purge_teaching_data, teaching_data_summary
from ..serializers import (DeleteAccountSerializer, GoogleLoginSerializer,
                           ReviewTeacherApplicationSerializer,
                           TeacherApplicationSerializer)

logger = logging.getLogger(__name__)


NICKNAME_RE = re.compile(r"^[\w가-힣][\w가-힣 ._-]{1,19}$")


def validate_nickname(nickname):
    """닉네임은 곧 계정 식별자이자 공개 표시 이름이다. 실패 시 사유를 돌려준다."""
    nickname = (nickname or "").strip()
    if not NICKNAME_RE.match(nickname):
        return None, "닉네임은 2~20자의 한글·영문·숫자로 입력해주세요"
    if is_reserved_username(nickname):
        # 접두어 전체를 막는다. 자릿수까지 맞춘 것만 막으면 "학생1" 같은 값이
        # 통과해 수업용 학생 계정과 헷갈린다.
        return None, RESERVED_USERNAME_PREFIX_MESSAGE
    if User.objects.filter(username__iexact=nickname).exists():
        return None, "이미 사용 중인 닉네임입니다"
    return nickname, None


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
            # 같은 이메일의 기존 계정이 있으면 구글 계정을 연결한다.
            # 단, 교사가 만들어 준 학생 계정은 아이디/PIN 으로만 로그인한다.
            existing = User.objects.filter(email=email).first() if email else None
            if existing is not None:
                if existing.created_by_id is not None:
                    return self.error("학교에서 발급받은 계정입니다. 선생님께 문의하세요")
                existing.google_sub = sub
                existing.save(update_fields=["google_sub"])
                user = existing
            else:
                # 신규 가입 — 가입이 닫혀 있으면 만들지 않는다(기존 사용자 로그인은 항상 허용)
                if not SysOptions.allow_register:
                    return self.error("현재 신규 가입을 받고 있지 않습니다")

                nickname = request.data.get("nickname")
                if not nickname:
                    # 프론트가 닉네임 입력 화면을 띄우도록 신호를 보낸다
                    return self.success({"status": "nickname_required"})
                nickname, error = validate_nickname(nickname)
                if error:
                    return self.error(error)

                user = User.objects.create(username=nickname,
                                           email=email or None,
                                           google_sub=sub,
                                           admin_type=AdminType.REGULAR_USER)
                user.set_unusable_password()
                user.save()
                UserProfile.objects.create(user=user)

        if user.is_disabled:
            return self.error("비활성화된 계정입니다")

        # 승인 여부와 무관하게 로그인시킨다.
        # 교사 신청은 로그인 후 별도 화면에서 진행한다.
        auth.login(request, user)
        return self.success({"status": "logged_in"})


class AccountDeleteAPI(APIView):
    """회원 탈퇴. 구글로 가입한 사용자만 스스로 나갈 수 있다.

    - 관리자(root 등)는 자기가 만든 문제·대회·공지가 함께 지워지므로 막는다.
    - 수업용 학생은 교사가 만들어 준 계정이라 스스로 지우지 않는다.
      교사가 지우거나, 교사가 탈퇴하면 함께 사라진다.
    """
    @login_required
    def get(self, request):
        """탈퇴하면 무엇이 함께 지워지는지 미리 보여준다"""
        error = self._check_deletable(request.user)
        if error:
            return self.error(error)
        return self.success({
            **teaching_data_summary(request.user),
            "submission_count": request.user.submissions.count(),
        })

    @validate_serializer(DeleteAccountSerializer)
    @login_required
    def post(self, request):
        user = request.user
        error = self._check_deletable(user)
        if error:
            return self.error(error)

        client_id = SysOptions.google_client_id
        if not client_id:
            return self.error("구글 로그인이 설정되지 않았습니다. 관리자에게 문의하세요")
        claims = verify_google_token(request.data["credential"], client_id)
        if not claims:
            return self.error("구글 인증에 실패했습니다. 다시 시도해주세요")
        # 남의 구글 계정으로는 지울 수 없다
        if claims.get("sub") != user.google_sub:
            return self.error("지금 로그인한 계정과 다른 구글 계정입니다")

        with transaction.atomic():
            # 본인이 확인 화면에서 내용을 보고 누른 것이라 여기서 바로 지운다.
            # (관리자가 남의 계정을 지울 때는 정리 기능을 먼저 거치게 한다)
            summary = purge_teaching_data(user)
            user.delete()
        auth.logout(request)
        return self.success({"deleted_students": summary["student_count"]})

    @staticmethod
    def _check_deletable(user):
        if user.is_admin_role():
            return "관리자 계정은 이 화면에서 탈퇴할 수 없습니다"
        if not user.google_sub:
            return "구글로 가입한 계정만 탈퇴할 수 있습니다. 선생님이나 관리자에게 문의하세요"


class TeacherApplicationAPI(APIView):
    @login_required
    def get(self, request):
        """내 신청 상태 조회"""
        application = TeacherApplication.objects.filter(user=request.user).first()
        if not application:
            return self.success(None)
        return self.success(TeacherApplicationSerializer(application).data)

    @login_required
    def post(self, request):
        """교사 신청. 로그인한 일반 사용자가 직접 누른다."""
        user = request.user
        if user.is_teacher() or user.is_admin_role():
            return self.error("이미 교사 권한이 있습니다")
        if user.created_by_id is not None:
            return self.error("학교에서 발급받은 계정은 교사 신청을 할 수 없습니다")

        application = TeacherApplication.objects.filter(user=user).first()
        if application:
            if application.status == TeacherApplicationStatus.PENDING:
                return self.error("이미 신청하셨습니다. 승인을 기다려주세요")
            if application.status == TeacherApplicationStatus.REJECTED:
                return self.error("신청이 반려되었습니다. 관리자에게 문의하세요")
            # 승인받았다가 관리자가 유형을 되돌린 경우다. user 가 OneToOne 이라
            # 새로 만들면 IntegrityError 로 500 이 난다. 기존 신청을 다시 세운다.
            application.status = TeacherApplicationStatus.PENDING
            application.reviewed_at = None
            application.reviewed_by = None
            application.note = ""
            application.save(update_fields=["status", "reviewed_at", "reviewed_by", "note"])
            return self.success(TeacherApplicationSerializer(application).data)

        application = TeacherApplication.objects.create(user=user)
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


class SchoolSyncAPI(APIView):
    """나이스에서 학교 목록을 적재한다. 최고관리자 전용."""
    @super_admin_required
    def get(self, request):
        from ..models import School
        status = dict(SysOptions.school_sync_status or {})
        status["school_count"] = School.objects.count()
        status["api_key_set"] = bool(SysOptions.neis_api_key)
        return self.success(status)

    @super_admin_required
    def post(self, request):
        from ..tasks import sync_schools_async
        if not SysOptions.neis_api_key:
            return self.error("먼저 나이스 API 키를 저장하세요")
        from ..neis import is_running, set_status
        if is_running():
            return self.error("이미 적재가 진행 중입니다")

        set_status(state="running", processed=0, total=0, message="", finished_at=None)
        sync_schools_async.send()
        return self.success({"state": "running"})
