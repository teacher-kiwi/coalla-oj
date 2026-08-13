import ipaddress

from account.decorators import login_required, check_contest_permission
from contest.models import ContestStatus, ContestRuleType
from judge.tasks import judge_task
from options.options import SysOptions
# from judge.dispatcher import JudgeDispatcher
from problem.models import Problem, ProblemRuleType
from utils.api import APIView, validate_serializer
from utils.cache import cache
from utils.captcha import Captcha
from utils.throttling import TokenBucket
from account.models import display_name_prefetch, my_student_ids
from ..models import Submission
from ..serializers import CreateSubmissionSerializer, SubmissionModelSerializer
from ..serializers import SubmissionSafeModelSerializer, SubmissionListSerializer


class SubmissionAPI(APIView):
    def throttling(self, request):
        user_bucket = TokenBucket(key=str(request.user.id),
                                  redis_conn=cache, **SysOptions.throttling["user"])
        can_consume, wait = user_bucket.consume()
        if not can_consume:
            return "Please wait %d seconds" % (int(wait))

        # ip_bucket = TokenBucket(key=request.session["ip"],
        #                         redis_conn=cache, **SysOptions.throttling["ip"])
        # can_consume, wait = ip_bucket.consume()
        # if not can_consume:
        #     return "보안 문자를 입력해야 합니다"

    @check_contest_permission(check_type="problems")
    def check_contest_permission(self, request):
        contest = self.contest
        if contest.status == ContestStatus.CONTEST_ENDED:
            return self.error("종료된 대회입니다")
        if not request.user.is_contest_admin(contest):
            user_ip = ipaddress.ip_address(request.session.get("ip"))
            if contest.allowed_ip_ranges:
                if not any(user_ip in ipaddress.ip_network(cidr, strict=False) for cidr in contest.allowed_ip_ranges):
                    return self.error("이 대회에서 허용되지 않은 IP입니다")

    @validate_serializer(CreateSubmissionSerializer)
    @login_required
    def post(self, request):
        data = request.data
        hide_id = False
        if data.get("contest_id"):
            error = self.check_contest_permission(request)
            if error:
                return error
            contest = self.contest
            if not contest.problem_details_permission(request.user):
                hide_id = True

        if data.get("captcha"):
            if not Captcha(request).check(data["captcha"]):
                return self.error("보안 문자가 올바르지 않습니다")
        error = self.throttling(request)
        if error:
            return self.error(error)

        try:
            problem = Problem.objects.get(id=data["problem_id"], contest_id=data.get("contest_id"), visible=True)
        except Problem.DoesNotExist:
            return self.error("문제가 존재하지 않습니다")
        if data["language"] == "Block Coding":
            if "Python3" not in problem.languages:
                return self.error("블록 코딩은 이 문제에서 Python3가 허용되어야 사용할 수 있습니다")
        elif data["language"] not in problem.languages:
            return self.error(f"{data['language']} 언어는 이 문제에서 사용할 수 없습니다")
        
        submission = Submission.objects.create(user_id=request.user.id,
                                               language=data["language"],
                                               code=data["code"],
                                               problem_id=problem.id,
                                               ip=request.session["ip"],
                                               contest_id=data.get("contest_id"),
                                               blockly_state=data.get("blockly_state") or None)
        # use this for debug
        # JudgeDispatcher(submission.id, problem.id).judge()
        judge_task.send(submission.id, problem.id)
        if hide_id:
            return self.success()
        else:
            return self.success({"submission_id": submission.id})

    @login_required
    def get(self, request):
        submission_id = request.GET.get("id")
        if not submission_id:
            return self.error("잘못된 요청입니다. id가 필요합니다")
        try:
            submission = Submission.objects.select_related("problem").get(id=submission_id)
        except Submission.DoesNotExist:
            return self.error("제출 기록이 존재하지 않습니다")
        if not submission.check_user_permission(request.user):
            return self.error("이 제출 기록에 접근할 권한이 없습니다")

        if submission.problem.rule_type == ProblemRuleType.OI or request.user.is_admin_role():
            submission_data = SubmissionModelSerializer(submission).data
        else:
            submission_data = SubmissionSafeModelSerializer(submission).data
        return self.success(submission_data)


class SubmissionListAPI(APIView):
    def get(self, request):
        if not request.GET.get("limit"):
            return self.error("limit 값이 필요합니다")
        if request.GET.get("contest_id"):
            return self.error("잘못된 요청입니다")

        submissions = Submission.objects.filter(contest_id__isnull=True)\
            .select_related("problem__created_by", "user")\
            .prefetch_related(display_name_prefetch("user"))
        problem_id = request.GET.get("problem_id")
        myself = request.GET.get("myself")
        result = request.GET.get("result")
        username = request.GET.get("username")
        if problem_id:
            try:
                problem = Problem.objects.get(_id=problem_id, contest_id__isnull=True, visible=True)
            except Problem.DoesNotExist:
                return self.error("문제가 존재하지 않습니다")
            submissions = submissions.filter(problem=problem)
        if (myself and myself == "1") or not SysOptions.submission_list_show_all:
            submissions = submissions.filter(user_id=request.user.id)
        elif request.GET.get("my_students") == "1" and request.user.is_authenticated \
                and request.user.is_teacher():
            # 교사에게만 의미가 있다. 다른 사용자가 넣어도 조용히 무시한다.
            submissions = submissions.filter(user_id__in=my_student_ids(request.user))
        elif username:
            submissions = submissions.filter(user__username__icontains=username)
        if result:
            submissions = submissions.filter(result=result)
        data = self.paginate_data(request, submissions)
        data["results"] = SubmissionListSerializer(data["results"], many=True, user=request.user).data
        return self.success(data)


class ContestSubmissionListAPI(APIView):
    @check_contest_permission(check_type="submissions")
    def get(self, request):
        if not request.GET.get("limit"):
            return self.error("limit 값이 필요합니다")

        contest = self.contest
        submissions = Submission.objects.filter(contest_id=contest.id)\
            .select_related("problem__created_by", "user")\
            .prefetch_related(display_name_prefetch("user"))
        problem_id = request.GET.get("problem_id")
        myself = request.GET.get("myself")
        result = request.GET.get("result")
        username = request.GET.get("username")
        if problem_id:
            try:
                problem = Problem.objects.get(_id=problem_id, contest_id=contest.id, visible=True)
            except Problem.DoesNotExist:
                return self.error("문제가 존재하지 않습니다")
            submissions = submissions.filter(problem=problem)

        if myself and myself == "1":
            submissions = submissions.filter(user_id=request.user.id)
        elif username:
            submissions = submissions.filter(user__username__icontains=username)
        if result:
            submissions = submissions.filter(result=result)

        # filter the test submissions submitted before contest start
        if contest.status != ContestStatus.CONTEST_NOT_START:
            submissions = submissions.filter(create_time__gte=contest.start_time)

        # 封榜的时候只能看到自己的提交
        if contest.rule_type == ContestRuleType.ACM:
            if not contest.real_time_rank and not request.user.is_contest_admin(contest):
                submissions = submissions.filter(user_id=request.user.id)

        data = self.paginate_data(request, submissions)
        data["results"] = SubmissionListSerializer(data["results"], many=True, user=request.user).data
        return self.success(data)


class SubmissionExistsAPI(APIView):
    def get(self, request):
        if not request.GET.get("problem_id"):
            return self.error("잘못된 요청입니다. problem_id가 필요합니다")
        return self.success(request.user.is_authenticated and
                            Submission.objects.filter(problem_id=request.GET["problem_id"],
                                                      user_id=request.user.id).exists())
