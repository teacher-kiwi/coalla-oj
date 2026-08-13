from utils.constants import ContestRuleType  # noqa
from django.db import models
from django.utils.timezone import now
from utils.models import JSONField

from utils.constants import ContestStatus, ContestType
from account.models import User
from utils.models import RichTextField


class Contest(models.Model):
    title = models.TextField()
    description = RichTextField()
    # 순위를 실시간으로 보여줄지, 캐시된 순위를 보여줄지(봉인)
    real_time_rank = models.BooleanField()
    password = models.TextField(null=True)
    # ContestRuleType 중 하나
    rule_type = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    create_time = models.DateTimeField(auto_now_add=True)
    last_update_time = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    # false 면 삭제한 것과 같다
    visible = models.BooleanField(default=True)
    allowed_ip_ranges = JSONField(default=list)

    @property
    def status(self):
        if self.start_time > now():
            return ContestStatus.CONTEST_NOT_START
        elif self.end_time < now():
            return ContestStatus.CONTEST_ENDED
        else:
            return ContestStatus.CONTEST_UNDERWAY

    @property
    def contest_type(self):
        if self.password:
            return ContestType.PASSWORD_PROTECTED_CONTEST
        return ContestType.PUBLIC_CONTEST

    # 문제의 통계(제출 수·정답 수 등)를 볼 수 있는지
    def problem_details_permission(self, user):
        return self.rule_type == ContestRuleType.ACM or \
               self.status == ContestStatus.CONTEST_ENDED or \
               user.is_authenticated and user.is_contest_admin(self) or \
               self.real_time_rank

    class Meta:
        db_table = "contest"
        ordering = ("-start_time",)


class AbstractContestRank(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    submission_number = models.IntegerField(default=0)

    class Meta:
        abstract = True


class ACMContestRank(AbstractContestRank):
    accepted_number = models.IntegerField(default=0)
    # ACM 전용. 정답까지 걸린 시간 + 틀린 횟수 * 20분(패널티)
    total_time = models.IntegerField(default=0)
    # 문제 id 를 키로 갖는다
    # {"23": {"is_ac": True, "ac_time": 8999, "error_number": 2, "is_first_ac": True}}
    submission_info = JSONField(default=dict)

    class Meta:
        db_table = "acm_contest_rank"
        unique_together = (("user", "contest"),)


class OIContestRank(AbstractContestRank):
    total_score = models.IntegerField(default=0)
    # 문제 id -> 현재 점수 {"23": 333}
    submission_info = JSONField(default=dict)

    class Meta:
        db_table = "oi_contest_rank"
        unique_together = (("user", "contest"),)


class ContestAnnouncement(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    title = models.TextField()
    content = RichTextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    visible = models.BooleanField(default=True)
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "contest_announcement"
        ordering = ("-create_time",)
