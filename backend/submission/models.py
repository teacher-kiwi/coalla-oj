from django.db import models

from utils.constants import ContestStatus
from utils.models import JSONField
from account.models import ClassMembership, User
from problem.models import Problem
from contest.models import Contest

from utils.shortcuts import rand_str


class JudgeStatus:
    COMPILE_ERROR = -2
    WRONG_ANSWER = -1
    ACCEPTED = 0
    CPU_TIME_LIMIT_EXCEEDED = 1
    REAL_TIME_LIMIT_EXCEEDED = 2
    MEMORY_LIMIT_EXCEEDED = 3
    RUNTIME_ERROR = 4
    SYSTEM_ERROR = 5
    PENDING = 6
    JUDGING = 7
    PARTIALLY_ACCEPTED = 8


class Submission(models.Model):
    id = models.TextField(default=rand_str, primary_key=True, db_index=True)
    contest = models.ForeignKey(Contest, null=True, on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    create_time = models.DateTimeField(auto_now_add=True)
    # FK 로 두어 닉네임 변경이 모든 화면에 즉시 반영되게 한다.
    # (원본은 IntegerField + username 복사본이었다)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True,
                             related_name="submissions")
    code = models.TextField()
    result = models.IntegerField(db_index=True, default=JudgeStatus.PENDING)
    # 从JudgeServer返回的判题详情
    info = JSONField(default=dict)
    language = models.TextField()
    blockly_state = models.TextField(null=True, blank=True)
    shared = models.BooleanField(default=False)
    # 存储该提交所用时间和内存值，方便提交列表显示
    # {time_cost: "", memory_cost: "", err_info: "", score: 0}
    statistic_info = JSONField(default=dict)
    ip = models.TextField(null=True)

    def check_user_permission(self, user, check_share=True):
        if self.user_id == user.id or user.is_super_admin() or user.can_mgmt_all_problem() or self.problem.created_by_id == user.id:
            return True

        # 교사는 담당 학생의 코드를 본다(학습 지도가 목적). 범위는 "내가 만든 학급에
        # 속한 학생"까지다. 교사 전체로 넓히면 남의 반 학생 코드까지 열린다.
        if user.is_teacher() and ClassMembership.objects.filter(
                student_id=self.user_id, school_class__teacher_id=user.id).exists():
            return True

        if check_share:
            if self.contest and self.contest.status != ContestStatus.CONTEST_ENDED:
                return False
            if self.problem.share_submission or self.shared:
                return True
        return False

    class Meta:
        db_table = "submission"
        ordering = ("-create_time",)

    def __str__(self):
        return self.id
