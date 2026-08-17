from django.db import models
from django.db.models.functions import Length
from utils.models import JSONField

from account.models import SchoolClass, User
from contest.models import Contest
from utils.models import RichTextField
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


# 공개 문제의 표시 번호는 서버가 매긴다(백준처럼 1000 부터).
# 사람이 직접 정하면 중복도 나고 정렬도 깨지고, 출제 화면에 칸이 하나 더 필요하다.
FIRST_DISPLAY_ID = 1000


class Problem(models.Model):
    # 화면에 보이는 문제 번호(1000 등). DB pk 와 별개다.
    _id = models.TextField(db_index=True)
    contest = models.ForeignKey(Contest, null=True, on_delete=models.CASCADE)
    # 대회 문제를 공개 문제로도 열어둘지
    is_public = models.BooleanField(default=False)
    title = models.TextField()
    description = RichTextField()
    input_description = RichTextField()
    output_description = RichTextField()
    # [{input: "test", output: "123"}, ...]
    samples = JSONField()
    test_case_id = models.TextField()
    # [{"input_name": "1.in", "output_name": "1.out", "score": 0}]
    test_case_score = JSONField()
    hint = RichTextField(null=True)
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
    submission_number = models.BigIntegerField(default=0)
    accepted_number = models.BigIntegerField(default=0)
    # 결과별 제출 수 {JudgeStatus.ACCEPTED: 3, JudgeStatus.WRONG_ANSWER: 11}
    statistic_info = JSONField(default=dict)

    @classmethod
    def next_display_id(cls):
        """다음 공개 문제 번호. 대회 문제는 대회 안에서 A·B·C 로 보이므로 제외한다."""
        used = cls.objects.filter(contest_id__isnull=True).values_list("_id", flat=True)
        numbers = [int(v) for v in used if str(v).isdigit()]
        return str(max(numbers) + 1) if numbers else str(FIRST_DISPLAY_ID)

    @property
    def is_open_to_everyone(self):
        return self.visibility == ProblemVisibility.public and self.visible

    class Meta:
        db_table = "problem"
        unique_together = (("_id", "contest"),)
        # 표시 번호는 문자열이라 그냥 정렬하면 12 가 2 보다 앞에 온다.
        # 길이를 먼저 보면 숫자 순서가 되고, 대회의 A·B·C 도 자연스럽게 정렬된다.
        ordering = (Length("_id"), "_id")

    def add_submission_number(self):
        self.submission_number = models.F("submission_number") + 1
        self.save(update_fields=["submission_number"])

    def add_ac_number(self):
        self.accepted_number = models.F("accepted_number") + 1
        self.save(update_fields=["accepted_number"])


class ProblemSet(models.Model):
    """교사가 공개 문제를 묶어 학급에 배포하는 단위.

    대회(Contest)와 달리 순위·시간 제한이 없다. 수업에서 "이번 주에 풀 문제"를
    지정하는 용도이므로 배포(assignment)와 마감일만 갖는다.
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

    같은 문제집을 여러 학급에 배포할 수 있고 학급마다 마감일이 다를 수 있어
    문제집이 아니라 이 관계에 마감일을 둔다.
    """
    problem_set = models.ForeignKey(ProblemSet, on_delete=models.CASCADE, related_name="assignments")
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name="assignments")
    assigned_at = models.DateTimeField(auto_now_add=True)
    due_at = models.DateTimeField(null=True, blank=True)
    # 배포를 잠시 내릴 때 쓴다. 삭제하면 학생 화면에서 사라지지만 다시 배포하려면
    # 마감일을 다시 입력해야 하므로 켜고 끄는 수단을 따로 둔다.
    is_open = models.BooleanField(default=True)

    class Meta:
        db_table = "problem_set_assignment"
        unique_together = (("problem_set", "school_class"),)
        ordering = ("-assigned_at",)


def can_access_problem(problem, user):
    """이 사용자가 이 문제를 열어볼 수 있는지.

    - 공개 문제는 누구나 (단 운영상 감춘 문제 `visible=False` 는 제외)
    - 비공개·승인대기 문제는 만든 교사 본인, 최고관리자,
      그리고 그 문제가 담긴 문제집을 배포받은 학급의 학생
    """
    if problem.contest_id is not None:
        # 대회 문제는 대회 권한 검사(check_contest_permission)가 따로 판단한다
        return False
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
        is_open=True,
        problem_set__items__problem_id=problem.id,
        school_class__memberships__student_id=user.id).exists()
