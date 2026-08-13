from django.db import models
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


class ProblemDifficulty(object):
    High = "High"
    Mid = "Mid"
    Low = "Low"


class ProblemIOMode(Choices):
    standard = "Standard IO"
    file = "File IO"


def _default_io_mode():
    return {"io_mode": ProblemIOMode.standard, "input": "input.txt", "output": "output.txt"}


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
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
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

    class Meta:
        db_table = "problem"
        unique_together = (("_id", "contest"),)
        ordering = ("create_time",)

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
