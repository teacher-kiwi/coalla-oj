from django.db import models
from utils.models import JSONField

from account.models import SchoolClass, User
from contest.models import Contest
from utils.constants import Choices


class ProblemTag(models.Model):
    name = models.TextField(unique=True)
    aliases = JSONField(default=list)

    class Meta:
        db_table = "problem_tag"


class ProblemRuleType(Choices):
    ACM = "ACM"
    OI = "OI"


class ProblemVisibility(Choices):
    """문제를 누가 볼 수 있는지.

    admin 의 `visible` 과는 다른 축이다. `visible` 은 "목록에서 감추기"(운영용)이고,
    이 값은 "누구의 문제인지"를 뜻한다.

    화면에서는 private 을 "학급", public 을 "공개" 로 부른다. 대회의 학급/공개와
    같은 축이라 말을 맞췄다(frontend 의 SCOPE_TAG). 값은 그대로 두고 라벨만 다르다.
    """
    # 만든 교사와 그 교사가 문제집으로 배포한 학급만 볼 수 있다
    private = "private"
    # 공개를 신청해 관리자 승인을 기다리는 중. 접근 범위는 private 과 같다
    pending = "pending"
    # 공개 문제 목록에 나온다
    public = "public"


class ProblemIOMode(Choices):
    standard = "Standard IO"
    file = "File IO"


def _default_io_mode():
    return {"io_mode": ProblemIOMode.standard, "input": "input.txt", "output": "output.txt"}


# 대회 문제는 대회 안에서 A, B, C 로 보인다. 라벨을 저장하지 않고 order 로 만든다.
# 저장하면 문제를 빼거나 순서를 바꿀 때마다 라벨을 다시 매겨야 한다.
CONTEST_PROBLEM_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
# 대회 안 표시는 라벨 개수까지만 만들 수 있다
MAX_CONTEST_PROBLEMS = len(CONTEST_PROBLEM_LABELS)


def contest_problem_label(order):
    """대회 문제 순서(1부터)를 표시 라벨로. 1 -> A, 2 -> B."""
    if 1 <= order <= len(CONTEST_PROBLEM_LABELS):
        return CONTEST_PROBLEM_LABELS[order - 1]
    return str(order)


def contest_problem_order(label):
    """표시 라벨을 순서로. A -> 1. 대회 문제 주소(/contest/1/problem/A)를 읽을 때 쓴다."""
    label = (label or "").strip().upper()
    if len(label) == 1 and label in CONTEST_PROBLEM_LABELS:
        return CONTEST_PROBLEM_LABELS.index(label) + 1
    # 27번째부터는 라벨이 숫자다(contest_problem_label 참고)
    if label.isdigit() and int(label) > 0:
        return int(label)
    return None


class Problem(models.Model):
    title = models.TextField()
    description = models.TextField()
    input_description = models.TextField()
    output_description = models.TextField()
    # [{input: "test", output: "123"}, ...]
    samples = JSONField()
    test_case_id = models.TextField()
    # [{"input_name": "1.in", "output_name": "1.out", "score": 0}]
    test_case_score = JSONField()
    hint = models.TextField(null=True)
    languages = JSONField()
    template = JSONField()
    create_time = models.DateTimeField(auto_now_add=True)
    # auto_now 를 쓰면 통계 갱신 같은 저장에도 값이 바뀌어 직접 넣는다
    last_update_time = models.DateTimeField(null=True)
    # 공개된 문제는 만든 사람이 탈퇴해도 남는다(출제자만 빈칸이 된다).
    # 비공개 문제는 그 교사만 쓰던 것이라 탈퇴할 때 함께 지운다.
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    visibility = models.TextField(default=ProblemVisibility.public)
    time_limit = models.IntegerField()  # ms
    memory_limit = models.IntegerField()  # MB
    io_mode = JSONField(default=_default_io_mode)
    # 특수 채점(정답이 여러 개인 문제)
    spj = models.BooleanField(default=False)
    spj_language = models.TextField(null=True)
    spj_code = models.TextField(null=True)
    spj_version = models.TextField(null=True)
    spj_compile_ok = models.BooleanField(default=False)
    rule_type = models.TextField()
    visible = models.BooleanField(default=True)
    difficulty = models.TextField()
    tags = models.ManyToManyField(ProblemTag)
    source = models.TextField(null=True)
    # OI 규칙에서만 쓴다
    total_score = models.IntegerField(default=0)
    # 화면에 보이는 값. 지워진 몫(archived_*)과 지금 남아 있는 제출을 합친 결과다.
    submission_number = models.BigIntegerField(default=0)
    accepted_number = models.BigIntegerField(default=0)
    # 결과별 제출 수 {JudgeStatus.ACCEPTED: 3, JudgeStatus.WRONG_ANSWER: 11}
    statistic_info = JSONField(default=dict)

    # 지워진 학생들이 남긴 몫. 정답률은 "지금까지 몇 명이 도전해 몇 번 맞혔나" 라
    # 학생이 학년을 마치고 떠난 뒤에도 남아야 하는 값이다. 그런데 제출을 지우면
    # 셀 근거가 사라지므로, 지우기 직전에 여기로 옮겨 둔다.
    # 재채점은 살아 있는 제출만 다시 세고 여기에 더해서 위의 값을 만든다.
    archived_submission_number = models.BigIntegerField(default=0)
    archived_accepted_number = models.BigIntegerField(default=0)
    archived_statistic_info = JSONField(default=dict)

    # 출제자가 넣어 두는 정답 코드. 테스트케이스가 맞는지 확인하는 데만 쓴다.
    # 채점에는 쓰이지 않고, 저장을 막지도 않는다 - 참고용 도구다.
    # 학생에게 새면 답이 그대로 나가므로 ProblemSerializer 에서 뺀다.
    solver_language = models.TextField(null=True, blank=True)
    solver_code = models.TextField(null=True, blank=True)
    # 마지막 검증 결과. 테스트케이스가 바뀌면 지운다(그대로 두면 거짓말이 된다).
    solver_verified_at = models.DateTimeField(null=True, blank=True)
    solver_passed = models.BooleanField(default=False)
    solver_message = models.TextField(blank=True, default="")

    @property
    def display_id(self):
        """화면에 보이는 문제 번호. pk 를 그대로 쓴다.

        번호를 따로 매기면 "지금까지 쓴 것 중 가장 큰 값 + 1" 을 읽고 쓰는 사이에
        다른 요청이 끼어들 수 있어 중복을 막는 장치가 필요했다. pk 는 DB 가
        겹치지 않게 발급한다. 대회 안에서 보이는 A, B, C 는 ContestProblem 이 정한다.
        """
        return str(self.id)

    @property
    def is_open_to_everyone(self):
        return self.visibility == ProblemVisibility.public and self.visible

    class Meta:
        db_table = "problem"
        ordering = ("id",)

    def add_submission_number(self):
        self.submission_number = models.F("submission_number") + 1
        self.save(update_fields=["submission_number"])

    def add_ac_number(self):
        self.accepted_number = models.F("accepted_number") + 1
        self.save(update_fields=["accepted_number"])


class ContestProblem(models.Model):
    """대회에 담긴 문제.

    예전에는 문제를 복사해서 넣었다(Problem.contest FK). 그래서 같은 문제를 세 반
    대회에 쓰면 세 벌이 생겨 오타 하나도 세 번 고쳐야 했고, 대회가 끝나고 문제를
    공개로 돌리면 또 한 벌이 더 생겨 대회 때 제출 기록이 따라오지 않았다.

    이제 문제 자체는 한 벌이고 대회는 그것을 가리키기만 한다. 대회가 끝난 뒤
    문제를 공개로 돌리면 대회 때의 제출이 그대로 그 문제의 기록으로 남는다.
    """
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name="problems")
    # 대회에 담긴 문제는 지울 수 없다. 지우면 제출이 함께 사라지는데(Submission 이
    # CASCADE) 순위표의 submission_info 는 문제 id 를 키로 든 JSON 이라 아무도
    # 지우지 않는다. 없는 문제 칸이 순위표에 남고 정답 수도 계속 센다.
    problem = models.ForeignKey(Problem, on_delete=models.PROTECT, related_name="contest_entries")
    # 대회 안에서의 순서(1부터). 화면에는 A, B, C 로 보인다.
    order = models.PositiveIntegerField()
    # 대회 안에서만 센 값. 문제 자체의 누적과 따로 둔다. 같이 두면 예전에 공개로
    # 풀린 횟수가 대회 화면에 그대로 나와 난이도가 샌다.
    submission_number = models.BigIntegerField(default=0)
    accepted_number = models.BigIntegerField(default=0)
    statistic_info = JSONField(default=dict)

    @property
    def label(self):
        return contest_problem_label(self.order)

    @classmethod
    def next_order(cls, contest):
        """대회에 다음으로 넣을 자리. 맨 뒤에 붙인다."""
        last = cls.objects.filter(contest=contest).aggregate(models.Max("order"))["order__max"]
        return (last or 0) + 1

    @classmethod
    def repack(cls, contest):
        """번호를 1부터 다시 붙인다.

        가운데 문제를 빼면 라벨이 A, C 로 벌어진다. 문제를 빼는 것은 대회 시작
        전에만 되고 그때는 제출도 순위도 없으므로, 번호가 바뀌어도 어긋날 것이 없다.

        앞에서부터 당기므로 (대회, 순서) 유일 제약에 걸리지 않는다. i번째 항목의
        현재 순서는 항상 i 이상이고, 그 자리는 이미 비워진 뒤다.
        """
        entries = cls.objects.filter(contest=contest).order_by("order")
        for index, entry in enumerate(entries, start=1):
            if entry.order != index:
                cls.objects.filter(id=entry.id).update(order=index)

    class Meta:
        db_table = "contest_problem"
        # 같은 문제를 한 대회에 두 번 담을 수 없고, 한 자리에 두 문제가 올 수 없다.
        unique_together = (("contest", "problem"), ("contest", "order"))
        ordering = ("order",)


class ProblemSet(models.Model):
    """교사가 공개 문제를 묶어 학급에 배포하는 단위.

    대회(Contest)와 달리 순위·시간 제한이 없다. 수업에서 "이번 주에 풀 문제"를
    지정하는 용도이므로 배포(assignment)만 갖는다.
    """
    title = models.TextField()
    description = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="problem_sets")
    create_time = models.DateTimeField(auto_now_add=True)
    last_update_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "problem_set"
        ordering = ("-create_time",)


class ProblemSetItem(models.Model):
    """문제집에 담긴 문제. order 로 교사가 정한 순서를 유지한다."""
    problem_set = models.ForeignKey(ProblemSet, on_delete=models.CASCADE, related_name="items")
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="problem_set_items")
    order = models.IntegerField(default=0)

    class Meta:
        db_table = "problem_set_item"
        unique_together = (("problem_set", "problem"),)
        ordering = ("order", "id")


class ProblemSetAssignment(models.Model):
    """문제집을 학급에 배포한 기록.

    이 기록이 있는지가 곧 학생에게 보이는지다. 배포를 내리려면 지운다.
    (예전에는 기록을 두고 공개만 끄는 is_open 이 따로 있었는데, 학생 화면에서
     "배포 안 함" 과 구분되지 않아 배포 하나로 합쳤다. 마감일도 있었지만
     지나도 아무것도 막지 않는 표시용이라 없앴다 - 역할을 정하면 그때 다시 넣는다)
    """
    problem_set = models.ForeignKey(ProblemSet, on_delete=models.CASCADE, related_name="assignments")
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name="assignments")
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "problem_set_assignment"
        unique_together = (("problem_set", "school_class"),)
        ordering = ("-assigned_at",)


class ProblemFavorite(models.Model):
    """사용자가 담아둔 문제.

    문제 목록의 하트로 켜고 끈다. 푼 문제 표시(UserProfile 의 상태값)와는 다른
    축이다. 그쪽은 채점 결과라 사용자가 바꿀 수 없고, 이것은 "나중에 다시 볼 것"
    이라는 표시다.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="problem_favorites")
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "problem_favorite"
        unique_together = (("user", "problem"),)
        ordering = ("-created_at",)


def can_access_problem(problem, user):
    """이 사용자가 이 문제를 열어볼 수 있는지.

    - 공개 문제는 누구나 (단 운영상 감춘 문제 `visible=False` 는 제외)
    - 비공개·승인대기 문제는 만든 교사 본인, 최고관리자,
      그리고 그 문제가 담긴 문제집을 배포받은 학급의 학생

    대회에 담겨 있는지는 보지 않는다. 대회 안에서 여는 것은 대회 권한 검사
    (check_contest_permission)가 따로 판단하고, 대회 밖에서는 그 문제가 공개인지
    비공개인지가 그대로 답이다. 대회용으로 만든 문제를 비공개로 두면 대회 밖에서
    열리지 않고, 공개 문제로 대회를 열었다면 원래 열려 있던 문제다.
    """
    if problem.is_open_to_everyone:
        return True
    if not user.is_authenticated:
        return False
    # 만든 교사와 관리자는 고치기 위해 언제든 볼 수 있다
    if problem.created_by_id == user.id or user.is_super_admin():
        return True
    # 관리자가 감춘 문제(visible=False)는 문제집으로 배포됐더라도 학생이 열 수 없다.
    # 감추는 이유는 대개 "문제가 잘못됐다"이고, 그런 문제를 계속 붙들게 하면 안 된다.
    # (제출 경로도 visible=True 로 이미 막고 있어 여기서 막지 않으면 앞뒤가 어긋난다)
    if not problem.visible:
        return False
    return ProblemSetAssignment.objects.filter(
        problem_set__items__problem_id=problem.id,
        school_class__memberships__student_id=user.id).exists()
