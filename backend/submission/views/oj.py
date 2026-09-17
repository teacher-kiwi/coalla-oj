import ipaddress

from django.db.models import Q
from django.utils.timezone import now

from account.decorators import login_required, check_contest_permission
from contest.models import ContestStatus, ContestRuleType
from judge.run import read_run, start_run
from judge.tasks import judge_task, run_code_task
from options.options import SysOptions
from problem.models import (can_access_problem, ContestProblem, contest_problem_order,
                            Problem, ProblemRuleType)
from problem.utils import parse_problem_template, problem_id_or_none
from utils.shortcuts import int_or_none
from utils.api import APIView, validate_serializer
from utils.cache import cache
from utils.throttling import TokenBucket
from account.models import my_student_ids
from ..models import Submission
from ..serializers import CreateSubmissionSerializer, RunCodeSerializer, SubmissionModelSerializer
from ..serializers import SubmissionSafeModelSerializer, SubmissionListSerializer


class SubmissionAPI(APIView):
    def throttling(self, request):
        user_bucket = TokenBucket(key=str(request.user.id),
                                  redis_conn=cache, **SysOptions.throttling["user"])
        can_consume, wait = user_bucket.consume()
        if not can_consume:
            return f"제출이 너무 잦습니다. {int(wait)}초 후에 다시 시도해주세요"

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

    @staticmethod
    def resolve_problem(request, data):
        """제출할 수 있는 문제와 언어인지. 문제 화면의 실행도 같은 검사를 거친다.

        :return: (problem, None) 또는 (None, 오류 문구)
        """
        try:
            problem = Problem.objects.get(id=data["problem_id"], visible=True)
        except Problem.DoesNotExist:
            return None, "문제가 존재하지 않습니다"
        # 대회 제출이라면 그 대회에 담긴 문제여야 한다
        if data.get("contest_id") and not ContestProblem.objects.filter(
                contest_id=data["contest_id"], problem=problem).exists():
            return None, "문제가 존재하지 않습니다"
        # 비공개 문제에는 만든 교사와 배포받은 학급 학생만 제출할 수 있다.
        # (대회 문제는 check_contest_permission 이 이미 판단했다)
        if not data.get("contest_id") and not can_access_problem(problem, request.user):
            return None, "문제가 존재하지 않습니다"
        if data["language"] == "Block Coding":
            if "Python3" not in problem.languages:
                return None, "블록 코딩은 이 문제에서 Python3가 허용되어야 사용할 수 있습니다"
        elif data["language"] not in problem.languages:
            language = data["language"]
            return None, f"{language} 언어는 이 문제에서 사용할 수 없습니다"
        return problem, None

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

        error = self.throttling(request)
        if error:
            return self.error(error)

        problem, error = self.resolve_problem(request, data)
        if error:
            return self.error(error)

        submission = Submission.objects.create(user_id=request.user.id,
                                               language=data["language"],
                                               code=data["code"],
                                               problem_id=problem.id,
                                               ip=request.session["ip"],
                                               contest_id=data.get("contest_id"),
                                               blockly_state=data.get("blockly_state") or None)
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


class RunCodeAPI(SubmissionAPI):
    """문제 화면에서 자기 입력으로 코드를 한 번 돌려 본다(judge/run.py).

    제출과 같은 문제·언어·대회 권한 검사를 거치지만 제출은 만들지 않는다.
    빈도 제한은 제출과 다른 통을 쓴다. 같은 통이면 디버깅하다 제출을 못 하게
    되고, 실행은 제출보다 훨씬 자주 누른다.
    """
    # 사용자마다 10 번까지 몰아서 누를 수 있고, 6 초에 한 번씩 다시 채워진다
    THROTTLE = {"capacity": 10, "fill_rate": 1 / 6, "default_capacity": 10}

    def throttling(self, request):
        bucket = TokenBucket(key=f"run:{request.user.id}", redis_conn=cache, **self.THROTTLE)
        can_consume, wait = bucket.consume()
        if not can_consume:
            return f"실행이 너무 잦습니다. {int(wait) + 1}초 후에 다시 눌러주세요"

    @validate_serializer(RunCodeSerializer)
    @login_required
    def post(self, request):
        data = request.data
        if data.get("contest_id"):
            error = self.check_contest_permission(request)
            if error:
                return error

        error = self.throttling(request)
        if error:
            return self.error(error)

        problem, error = self.resolve_problem(request, data)
        if error:
            return self.error(error)

        # 제출과 똑같이 감싼다. 빠뜨리면 제출은 되는데 실행은 컴파일 에러가 난다.
        language = "Python3" if data["language"] == "Block Coding" else data["language"]
        code = data["code"]
        if language in problem.template:
            template = parse_problem_template(problem.template[language])
            code = "\n".join([template["prepend"], code, template["append"]])

        spec = {"language": language, "code": code, "input": data.get("input") or "",
                "time_limit": problem.time_limit, "memory_limit": problem.memory_limit,
                "io_mode": problem.io_mode}
        token = start_run(request.user.id)
        run_code_task.send(token, request.user.id, spec)
        return self.success({"token": token})

    @login_required
    def get(self, request):
        record = read_run(request.GET.get("token"), request.user.id)
        if not record:
            return self.error("실행 기록을 찾을 수 없습니다. 다시 실행해주세요")
        record = {k: v for k, v in record.items() if k != "user_id"}
        return self.success(record)


class SubmissionListAPI(APIView):
    def get(self, request):
        if not request.GET.get("limit"):
            return self.error("limit 값이 필요합니다")
        if request.GET.get("contest_id"):
            return self.error("잘못된 요청입니다")

        # 끝난 대회의 제출은 공개 목록에 함께 나온다. 대회 때 푼 것이 그 문제의
        # 기록으로 남는다는 뜻이다. 대회를 다시 열면(끝 시각을 미루면) 도로 숨는다.
        # 저장해두지 않고 그때그때 시각으로 판단하므로 되돌릴 상태가 없다.
        submissions = Submission.objects.filter(
            Q(contest__isnull=True) | Q(contest__end_time__lt=now())) \
            .select_related("problem__created_by", "user")
        problem_id = request.GET.get("problem_id")
        myself = request.GET.get("myself")
        result = request.GET.get("result")
        username = request.GET.get("username")
        if problem_id:
            number = problem_id_or_none(problem_id)
            problem = None
            if number is not None:
                problem = Problem.objects.filter(id=number, visible=True).first()
            if problem is None:
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
            .select_related("problem__created_by", "user")
        problem_id = request.GET.get("problem_id")
        myself = request.GET.get("myself")
        result = request.GET.get("result")
        username = request.GET.get("username")
        if problem_id:
            order = contest_problem_order(problem_id)
            entry = None
            if order is not None:
                entry = ContestProblem.objects.filter(contest_id=contest.id, order=order,
                                                      problem__visible=True).first()
            if entry is None:
                return self.error("문제가 존재하지 않습니다")
            submissions = submissions.filter(problem_id=entry.problem_id)

        if myself and myself == "1":
            submissions = submissions.filter(user_id=request.user.id)
        elif username:
            submissions = submissions.filter(user__username__icontains=username)
        if result:
            submissions = submissions.filter(result=result)

        # 대회 시작 전에 넣어본 테스트 제출은 제외한다
        if contest.status != ContestStatus.CONTEST_NOT_START:
            submissions = submissions.filter(create_time__gte=contest.start_time)

        # 순위를 봉인한 동안에는 자기 제출만 보인다. 끝난 뒤에는 가리지 않는다
        # (공개 제출 목록에는 이미 나오므로 여기서만 가리면 어긋난다).
        if contest.rule_type == ContestRuleType.ACM \
                and contest.status == ContestStatus.CONTEST_UNDERWAY:
            if not contest.real_time_rank and not request.user.is_contest_admin(contest):
                submissions = submissions.filter(user_id=request.user.id)

        data = self.paginate_data(request, submissions)
        data["results"] = SubmissionListSerializer(data["results"], many=True, user=request.user).data
        return self.success(data)


class SubmissionExistsAPI(APIView):
    """이 문제에 내가 제출한 적이 있는지.

    대회 안에서 물으면 그 대회 안 제출만 본다. 문제를 복사하지 않으므로, 범위를
    나누지 않으면 대회 밖에서 미리 풀어둔 기록이 "이미 제출했다" 로 보인다.
    """
    def get(self, request):
        problem_id = problem_id_or_none(request.GET.get("problem_id"))
        if problem_id is None:
            return self.error("잘못된 요청입니다. problem_id가 필요합니다")
        if not request.user.is_authenticated:
            return self.success(False)

        submissions = Submission.objects.filter(problem_id=problem_id, user_id=request.user.id)
        contest_id = int_or_none(request.GET.get("contest_id"))
        if contest_id is not None:
            submissions = submissions.filter(contest_id=contest_id)
        else:
            # 대회 밖에서는 공개 제출 목록과 같은 범위로 본다
            submissions = submissions.filter(
                Q(contest__isnull=True) | Q(contest__end_time__lt=now()))
        return self.success(submissions.exists())
