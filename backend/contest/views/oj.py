import io

import xlsxwriter
from django.http import HttpResponse
from django.db.models import Q
from django.utils.timezone import now
from django.core.cache import cache

from problem.models import Problem
from utils.api import APIView, validate_serializer
from utils.constants import CacheKey, CONTEST_PASSWORD_SESSION_KEY
from utils.shortcuts import datetime2str, check_is_id
from account.models import RANKED_ADMIN_TYPES
from account.decorators import login_required, check_contest_permission, check_contest_password

from utils.constants import ContestRuleType, ContestStatus
from ..models import ContestAnnouncement, Contest, OIContestRank, ACMContestRank
from ..serializers import ContestAnnouncementSerializer
from ..serializers import ContestSerializer, ContestPasswordVerifySerializer
from ..serializers import OIContestRankSerializer, ACMContestRankSerializer


def _class_contest_visible_to(user):
    """대회 목록에서 학급 대회를 걸러내는 조건."""
    public_only = Q(is_class_contest=False)
    if not user.is_authenticated:
        return public_only
    if user.is_super_admin():
        return Q()
    return public_only | Q(created_by=user) | Q(
        assignments__school_class__memberships__student_id=user.id)


class ContestAnnouncementListAPI(APIView):
    @check_contest_permission(check_type="announcements")
    def get(self, request):
        contest_id = request.GET.get("contest_id")
        if not contest_id:
            return self.error("잘못된 요청입니다. contest_id가 필요합니다")
        data = ContestAnnouncement.objects.select_related("created_by").filter(contest_id=contest_id, visible=True)
        max_id = request.GET.get("max_id")
        if max_id:
            data = data.filter(id__gt=max_id)
        return self.success(ContestAnnouncementSerializer(data, many=True).data)


class ContestAPI(APIView):
    def get(self, request):
        id = request.GET.get("id")
        if not id or not check_is_id(id):
            return self.error("잘못된 요청입니다. id가 필요합니다")
        try:
            contest = Contest.objects.get(id=id, visible=True)
        except Contest.DoesNotExist:
            return self.error("대회가 존재하지 않습니다")
        # 배포받지 않은 학급 대회는 없는 것과 같이 취급한다(존재를 알리지 않는다)
        if not contest.is_open_to(request.user):
            return self.error("대회가 존재하지 않습니다")
        data = ContestSerializer(contest).data
        data["now"] = datetime2str(now())
        return self.success(data)


class ContestListAPI(APIView):
    def get(self, request):
        contests = Contest.objects.select_related("created_by").filter(visible=True)
        # 학급 대회는 배포받은 학급의 학생과 만든 교사에게만 보인다.
        # 배포 조인 때문에 같은 대회가 여러 번 나올 수 있어 distinct 가 필요하다.
        contests = contests.filter(_class_contest_visible_to(request.user)).distinct()
        # 학생 화면에서 "우리 반 대회"와 "공개 대회"를 나눠 보기 위한 구분.
        # contest_type 이라는 이름은 이미 비밀번호 유무를 뜻해서 scope 를 쓴다.
        # 값이 없으면 지금처럼 둘 다 보여준다.
        scope = request.GET.get("scope")
        if scope == "class":
            contests = contests.filter(is_class_contest=True)
        elif scope == "public":
            contests = contests.filter(is_class_contest=False)
        keyword = request.GET.get("keyword")
        rule_type = request.GET.get("rule_type")
        status = request.GET.get("status")
        if keyword:
            contests = contests.filter(title__contains=keyword)
        if rule_type:
            contests = contests.filter(rule_type=rule_type)
        if status:
            cur = now()
            if status == ContestStatus.CONTEST_NOT_START:
                contests = contests.filter(start_time__gt=cur)
            elif status == ContestStatus.CONTEST_ENDED:
                contests = contests.filter(end_time__lt=cur)
            else:
                contests = contests.filter(start_time__lte=cur, end_time__gte=cur)
        return self.success(self.paginate_data(request, contests, ContestSerializer))


class ContestPasswordVerifyAPI(APIView):
    @validate_serializer(ContestPasswordVerifySerializer)
    @login_required
    def post(self, request):
        data = request.data
        try:
            contest = Contest.objects.get(id=data["contest_id"], visible=True, password__isnull=False)
        except Contest.DoesNotExist:
            return self.error("대회가 존재하지 않습니다")
        if not check_contest_password(data["password"], contest.password):
            return self.error("비밀번호가 올바르지 않거나 만료되었습니다")

        if CONTEST_PASSWORD_SESSION_KEY not in request.session:
            request.session[CONTEST_PASSWORD_SESSION_KEY] = {}
        request.session[CONTEST_PASSWORD_SESSION_KEY][contest.id] = data["password"]
        # 중첩 dict 를 바꾼 것만으로는 세션이 저장되지 않는다
        # https://docs.djangoproject.com/en/4.2/topics/http/sessions/#when-sessions-are-saved
        request.session.modified = True
        return self.success(True)


class ContestAccessAPI(APIView):
    @login_required
    def get(self, request):
        contest_id = request.GET.get("contest_id")
        if not contest_id:
            return self.error()
        try:
            contest = Contest.objects.get(id=contest_id, visible=True, password__isnull=False)
        except Contest.DoesNotExist:
            return self.error("대회가 존재하지 않습니다")
        session_pass = request.session.get(CONTEST_PASSWORD_SESSION_KEY, {}).get(contest.id)
        return self.success({"access": check_contest_password(session_pass, contest.password)})


class ContestRankAPI(APIView):
    def get_rank(self):
        if self.contest.rule_type == ContestRuleType.ACM:
            return ACMContestRank.objects.filter(contest=self.contest,
                                                 user__admin_type__in=RANKED_ADMIN_TYPES,
                                                 user__is_disabled=False).\
                select_related("user").order_by("-accepted_number", "total_time")
        else:
            return OIContestRank.objects.filter(contest=self.contest,
                                                user__admin_type__in=RANKED_ADMIN_TYPES,
                                                user__is_disabled=False). \
                select_related("user").order_by("-total_score")

    def column_string(self, n):
        string = ""
        while n > 0:
            n, remainder = divmod(n - 1, 26)
            string = chr(65 + remainder) + string
        return string

    @check_contest_permission(check_type="ranks")
    def get(self, request):
        download_csv = request.GET.get("download_csv")
        force_refresh = request.GET.get("force_refresh")
        is_contest_admin = request.user.is_authenticated and request.user.is_contest_admin(self.contest)
        if self.contest.rule_type == ContestRuleType.OI:
            serializer = OIContestRankSerializer
        else:
            serializer = ACMContestRankSerializer

        if force_refresh == "1" and is_contest_admin:
            qs = self.get_rank()
        else:
            cache_key = f"{CacheKey.contest_rank_cache}:{self.contest.id}"
            qs = cache.get(cache_key)
            if not qs:
                qs = self.get_rank()
                cache.set(cache_key, qs)

        if download_csv:
            data = serializer(qs, many=True, is_contest_admin=is_contest_admin).data
            contest_problems = Problem.objects.filter(contest=self.contest, visible=True).order_by("order")
            problem_ids = [item.id for item in contest_problems]

            f = io.BytesIO()
            workbook = xlsxwriter.Workbook(f)
            worksheet = workbook.add_worksheet()
            worksheet.write("A1", "User ID")
            worksheet.write("B1", "Username")
            if self.contest.rule_type == ContestRuleType.OI:
                worksheet.write("C1", "Total Score")
                for item in range(contest_problems.count()):
                    worksheet.write(self.column_string(4 + item) + "1", f"{contest_problems[item].title}")
                for index, item in enumerate(data):
                    worksheet.write_string(index + 1, 0, str(item["user"]["id"]))
                    worksheet.write_string(index + 1, 1, item["user"]["username"])
                    worksheet.write_string(index + 1, 2, str(item["total_score"]))
                    for k, v in item["submission_info"].items():
                        worksheet.write_string(index + 1, 3 + problem_ids.index(int(k)), str(v))
            else:
                worksheet.write("C1", "AC")
                worksheet.write("D1", "Total Submission")
                worksheet.write("E1", "Total Time")
                for item in range(contest_problems.count()):
                    worksheet.write(self.column_string(6 + item) + "1", f"{contest_problems[item].title}")

                for index, item in enumerate(data):
                    worksheet.write_string(index + 1, 0, str(item["user"]["id"]))
                    worksheet.write_string(index + 1, 1, item["user"]["username"])
                    worksheet.write_string(index + 1, 2, str(item["accepted_number"]))
                    worksheet.write_string(index + 1, 3, str(item["submission_number"]))
                    worksheet.write_string(index + 1, 4, str(item["total_time"]))
                    for k, v in item["submission_info"].items():
                        worksheet.write_string(index + 1, 5 + problem_ids.index(int(k)), str(v["is_ac"]))

            workbook.close()
            f.seek(0)
            response = HttpResponse(f.read())
            response["Content-Disposition"] = f"attachment; filename=content-{self.contest.id}-rank.xlsx"
            response["Content-Type"] = "application/xlsx"
            return response

        page_qs = self.paginate_data(request, qs)
        page_qs["results"] = serializer(page_qs["results"], many=True, is_contest_admin=is_contest_admin).data
        return self.success(page_qs)
