import os
from datetime import timedelta
from importlib import import_module

from django.conf import settings
from django.contrib import auth
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt

from problem.models import Problem
from utils.constants import ContestRuleType
from options.options import SysOptions
from utils.api import APIView, validate_serializer, CSRFExemptAPIView
from utils.captcha import Captcha
from utils.shortcuts import rand_str, datetime2str
from ..decorators import login_required
from ..models import (display_name_prefetch, has_public_profile, my_student_ids,
                      User, UserProfile, AdminType)
from ..serializers import (ApplyResetPasswordSerializer, ResetPasswordSerializer,
                           UserChangePasswordSerializer, UserLoginSerializer,
                           UsernameOrEmailCheckSerializer,
                           RankInfoSerializer, UserChangeEmailSerializer, SSOSerializer)
from ..serializers import (UserProfileSerializer,
                           EditUserProfileSerializer, ImageUploadForm)
from ..tasks import send_email_async


class UserProfileAPI(APIView):
    @method_decorator(ensure_csrf_cookie)
    def get(self, request, **kwargs):
        """로그인 여부를 판단하고, 로그인 상태면 사용자 정보를 돌려준다."""
        user = request.user
        if not user.is_authenticated:
            return self.success()
        show_real_name = False
        username = request.GET.get("username")
        try:
            if username:
                user = User.objects.get(username=username, is_disabled=False)
                # 수업용 학생의 프로필은 남에게 열지 않는다. 표시 이름("○○학교 학생")으로는
                # 애초에 찾을 수 없고, 내부 아이디를 알아내 조회하면 학교·반·번호가 드러난다.
                if not has_public_profile(user) and user.id != request.user.id:
                    return self.error("사용자가 존재하지 않습니다")
            else:
                user = request.user
                # 자기 정보를 돌려주는 경우라 real_name 도 포함한다
                show_real_name = True
        except User.DoesNotExist:
            return self.error("사용자가 존재하지 않습니다")
        return self.success(UserProfileSerializer(user.userprofile, show_real_name=show_real_name).data)

    @validate_serializer(EditUserProfileSerializer)
    @login_required
    def put(self, request):
        data = request.data
        user_profile = request.user.userprofile
        for k, v in data.items():
            setattr(user_profile, k, v)
        user_profile.save()
        return self.success(UserProfileSerializer(user_profile, show_real_name=True).data)


class AvatarUploadAPI(APIView):
    request_parsers = ()

    @login_required
    def post(self, request):
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            avatar = form.cleaned_data["image"]
        else:
            return self.error("파일 내용이 올바르지 않습니다")
        if avatar.size > 2 * 1024 * 1024:
            return self.error("이미지 크기가 너무 큽니다")
        suffix = os.path.splitext(avatar.name)[-1].lower()
        if suffix not in [".gif", ".jpg", ".jpeg", ".bmp", ".png"]:
            return self.error("지원하지 않는 파일 형식입니다")

        name = rand_str(10) + suffix
        with open(os.path.join(settings.AVATAR_UPLOAD_DIR, name), "wb") as img:
            for chunk in avatar:
                img.write(chunk)
        user_profile = request.user.userprofile

        user_profile.avatar = f"{settings.AVATAR_URI_PREFIX}/{name}"
        user_profile.save()
        return self.success("Succeeded")


class UserLoginAPI(APIView):
    @validate_serializer(UserLoginSerializer)
    def post(self, request):
        data = request.data
        user = auth.authenticate(username=data["username"], password=data["password"])
        if user:
            if user.is_disabled:
                return self.error("비활성화된 계정입니다")
            auth.login(request, user)
            return self.success("Succeeded")
        else:
            return self.error("사용자명 또는 비밀번호가 올바르지 않습니다")


class UserLogoutAPI(APIView):
    def get(self, request):
        auth.logout(request)
        return self.success()


class UsernameOrEmailCheck(APIView):
    @validate_serializer(UsernameOrEmailCheckSerializer)
    def post(self, request):
        data = request.data
        # True 면 이미 사용 중이라는 뜻
        result = {
            "username": False,
            "email": False
        }
        if data.get("username"):
            result["username"] = User.objects.filter(username=data["username"].lower()).exists()
        if data.get("email"):
            result["email"] = User.objects.filter(email=data["email"].lower()).exists()
        return self.success(result)


class UserRegisterAPI(APIView):
    """옛 아이디/비밀번호 회원가입. 더 이상 사용하지 않는다.

    일반 회원(교사·개인학생)은 구글로만 가입하고(GoogleLoginAPI),
    수업용 학생 계정은 교사가 만들어 준다.
    이 경로를 열어두면 닉네임 정책과 구글 연동을 우회하는 두 번째 통로가 된다.
    """
    def post(self, request):
        return self.error("구글 계정으로 가입해주세요")


class UserChangeEmailAPI(APIView):
    @validate_serializer(UserChangeEmailSerializer)
    @login_required
    def post(self, request):
        data = request.data
        user = auth.authenticate(username=request.user.username, password=data["password"])
        if user:
            data["new_email"] = data["new_email"].lower()
            if User.objects.filter(email=data["new_email"]).exists():
                return self.error("다른 계정이 사용 중인 이메일입니다")
            user.email = data["new_email"]
            user.save()
            return self.success("Succeeded")
        else:
            return self.error("비밀번호가 올바르지 않습니다")


class UserChangePasswordAPI(APIView):
    @validate_serializer(UserChangePasswordSerializer)
    @login_required
    def post(self, request):
        data = request.data
        username = request.user.username
        user = auth.authenticate(username=username, password=data["old_password"])
        if user:
            user.set_password(data["new_password"])
            user.save()
            return self.success("Succeeded")
        else:
            return self.error("기존 비밀번호가 올바르지 않습니다")


class ApplyResetPasswordAPI(APIView):
    @validate_serializer(ApplyResetPasswordSerializer)
    def post(self, request):
        if request.user.is_authenticated:
            return self.error("이미 로그인되어 있습니다")
        data = request.data
        captcha = Captcha(request)
        if not captcha.check(data["captcha"]):
            return self.error("보안 문자가 올바르지 않습니다")
        try:
            user = User.objects.get(email__iexact=data["email"])
        except User.DoesNotExist:
            return self.error("사용자가 존재하지 않습니다")
        if user.google_sub:
            return self.error("구글 계정으로 가입하셨습니다. 구글로 로그인해주세요")
        if user.created_by_id is not None:
            return self.error("학교에서 발급받은 계정입니다. 선생님께 문의하세요")
        if user.reset_password_token_expire_time and 0 < int(
                (user.reset_password_token_expire_time - now()).total_seconds()) < 20 * 60:
            return self.error("비밀번호 재설정은 20분에 한 번만 요청할 수 있습니다")
        user.reset_password_token = rand_str()
        user.reset_password_token_expire_time = now() + timedelta(minutes=20)
        user.save()
        render_data = {
            "username": user.username,
            "website_name": SysOptions.website_name,
            "link": f"{SysOptions.website_base_url}/reset-password/{user.reset_password_token}"
        }
        email_html = render_to_string("reset_password_email.html", render_data)
        send_email_async.send(from_name=SysOptions.website_name_shortcut,
                              to_email=user.email,
                              to_name=user.username,
                              subject="비밀번호 재설정 안내",
                              content=email_html)
        return self.success("Succeeded")


class ResetPasswordAPI(APIView):
    @validate_serializer(ResetPasswordSerializer)
    def post(self, request):
        data = request.data
        captcha = Captcha(request)
        if not captcha.check(data["captcha"]):
            return self.error("보안 문자가 올바르지 않습니다")
        try:
            user = User.objects.get(reset_password_token=data["token"])
        except User.DoesNotExist:
            return self.error("토큰이 존재하지 않습니다")
        if user.reset_password_token_expire_time < now():
            return self.error("토큰이 만료되었습니다")
        user.reset_password_token = None
        user.set_password(data["password"])
        user.save()
        return self.success("Succeeded")


class SessionManagementAPI(APIView):
    @login_required
    def get(self, request):
        engine = import_module(settings.SESSION_ENGINE)
        session_store = engine.SessionStore
        current_session = request.session.session_key
        session_keys = request.user.session_keys
        result = []
        modified = False
        for key in session_keys[:]:
            session = session_store(key)
            # 세션이 없거나 만료됐다
            if not session._session:
                session_keys.remove(key)
                modified = True
                continue

            # 현재 세션은 저장소보다 request.session 이 최신이다.
            # 미들웨어가 방금 넣은 ip/user_agent 는 응답 시점에야 저장되기 때문에,
            # 로그인 직후 첫 요청에서는 저장소 사본에 아직 없을 수 있다.
            is_current = current_session == key
            source = request.session if is_current else session

            s = {}
            if is_current:
                s["current_session"] = True
            s["ip"] = source.get("ip", "")
            s["user_agent"] = source.get("user_agent", "")
            last_activity = source.get("last_activity")
            s["last_activity"] = datetime2str(last_activity) if last_activity else None
            s["session_key"] = key
            result.append(s)
        if modified:
            request.user.save()
        return self.success(result)

    @login_required
    def delete(self, request):
        session_key = request.GET.get("session_key")
        if not session_key:
            return self.error("잘못된 요청입니다")
        request.session.delete(session_key)
        if session_key in request.user.session_keys:
            request.user.session_keys.remove(session_key)
            request.user.save()
            return self.success("Succeeded")
        else:
            return self.error("session_key가 올바르지 않습니다")


class UserRankAPI(APIView):
    def get(self, request):
        rule_type = request.GET.get("rule")
        if rule_type not in ContestRuleType.choices():
            rule_type = ContestRuleType.ACM
        profiles = UserProfile.objects.filter(user__admin_type=AdminType.REGULAR_USER, user__is_disabled=False) \
            .select_related("user") \
            .prefetch_related(display_name_prefetch("user"))
        # 교사가 자기 학생들끼리의 순위를 볼 수 있게 한다. 학생은 같은 학교 학생끼리
        # 서로 구분되지 않으므로(표시 이름이 학교명뿐) 공개 순위는 그대로 둔다.
        if request.GET.get("my_students") == "1" and request.user.is_authenticated \
                and request.user.is_teacher():
            profiles = profiles.filter(user_id__in=my_student_ids(request.user))
        if rule_type == ContestRuleType.ACM:
            profiles = profiles.filter(submission_number__gt=0).order_by("-accepted_number", "submission_number")
        else:
            profiles = profiles.filter(total_score__gt=0).order_by("-total_score")
        return self.success(self.paginate_data(request, profiles, RankInfoSerializer))


class ProfileProblemDisplayIDRefreshAPI(APIView):
    @login_required
    def get(self, request):
        profile = request.user.userprofile
        acm_problems = profile.acm_problems_status.get("problems", {})
        oi_problems = profile.oi_problems_status.get("problems", {})
        ids = list(acm_problems.keys()) + list(oi_problems.keys())
        if not ids:
            return self.success()
        # id 로 짝지어야 한다. 예전에는 zip(ids, display_ids) 로 조회 순서에 기댔는데,
        # 순서가 보장되지 않아 엉뚱한 표시 ID 가 들어갔고 숨김·삭제된 문제가 있으면
        # 개수가 어긋나 KeyError 로 터졌다.
        id_map = {str(pk): _id for pk, _id in
                  Problem.objects.filter(id__in=ids, visible=True).values_list("id", "_id")}
        for problems in (acm_problems, oi_problems):
            for k, v in problems.items():
                if k in id_map:
                    v["_id"] = id_map[k]
        profile.save(update_fields=["acm_problems_status", "oi_problems_status"])
        return self.success()


class SSOAPI(CSRFExemptAPIView):
    @login_required
    def get(self, request):
        token = rand_str()
        request.user.auth_token = token
        request.user.save()
        return self.success({"token": token})

    @method_decorator(csrf_exempt)
    @validate_serializer(SSOSerializer)
    def post(self, request):
        try:
            user = User.objects.get(auth_token=request.data["token"])
        except User.DoesNotExist:
            return self.error("사용자가 존재하지 않습니다")
        return self.success({"username": user.username, "avatar": user.userprofile.avatar, "admin_type": user.admin_type})
