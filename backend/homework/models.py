"""바로 과제: 계정 없이 6자리 코드로 들어와 푸는 일회성 과제.

수업(문제집·학급 배포)과는 별개다. 학생은 번호(1~5자리 숫자)·닉네임·4자리 숫자로
들어오고, 들어오는 순간 보이지 않는 임시 계정(AdminType.GUEST)이 하나 생긴다.
제출·채점은 그 계정으로 기존 흐름을 그대로 탄다. 제출이 늘 사용자에 묶여 있어서
계정 없는 제출을 따로 만들면 채점·권한·통계를 전부 손대야 하기 때문이다.

기록은 교사가 과제를 지울 때까지 남는다. 지우면 참가자의 임시 계정까지 지워
제출이 함께 사라진다(post_delete 신호).
"""
import secrets

from django.db import IntegrityError, models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.timezone import now

from account.models import AdminType, User, UserProfile
from problem.models import Problem
from utils.api import APIError
from utils.models import JSONField

# 0 으로 시작하면 받아 적다 빠뜨리기 쉬워 100000 부터 쓴다
CODE_MIN, CODE_MAX = 100000, 999999
GUEST_USERNAME_PREFIX = "바로과제"
MAX_NUMBER = 99999
NICKNAME_MAX_LENGTH = 20


class Homework(models.Model):
    # 지울 때까지 다른 과제에 다시 쓰지 않는다. 옛 링크로 엉뚱한 과제에 들어가면 안 된다.
    code = models.CharField(max_length=6, unique=True)
    title = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="homeworks")
    # 교사가 고른 언어. 문제마다 허용된 언어와 겹치는 것만 쓸 수 있다.
    languages = JSONField(default=list)
    end_time = models.DateTimeField()
    # 교사가 마감 전에 종료를 누른 시각. 마감이 지나면 누르지 않아도 종료다.
    ended_at = models.DateTimeField(null=True)
    # 새 입장 막기. 이미 들어온 학생은 그대로 들어올 수 있다.
    entry_locked = models.BooleanField(default=False)
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "homework"
        ordering = ("-create_time",)

    @property
    def is_ended(self):
        return self.ended_at is not None or now() >= self.end_time

    def problems(self):
        return [item.problem for item in self.items.select_related("problem").order_by("order", "id")]

    @staticmethod
    def generate_code():
        """지금 쓰이지 않는 코드. DB 의 유니크 제약이 최종 방어선이다."""
        taken = set(Homework.objects.values_list("code", flat=True))
        if len(taken) > (CODE_MAX - CODE_MIN) // 2:
            raise APIError("과제 코드가 모자랍니다. 지난 과제를 지운 뒤 다시 만들어주세요")
        while True:
            code = str(secrets.randbelow(CODE_MAX - CODE_MIN + 1) + CODE_MIN)
            if code not in taken:
                return code


class HomeworkProblem(models.Model):
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE, related_name="items")
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="homework_items")
    order = models.IntegerField(default=0)

    class Meta:
        db_table = "homework_problem"
        unique_together = (("homework", "problem"),)


class HomeworkParticipant(models.Model):
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE, related_name="participants")
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="homework_participant")
    # 출석번호든 학번이든 교사가 정한 대로. "05" 와 "5" 는 같은 번호다.
    number = models.IntegerField()
    nickname = models.TextField()
    # 교사에게 보이는 값이라 해시하지 않는다. 비밀번호가 아니라 자리 확인용이다.
    pin = models.CharField(max_length=4)
    join_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "homework_participant"
        unique_together = (("homework", "number"),)
        ordering = ("number",)

    def pin_matches(self, pin):
        return secrets.compare_digest(self.pin, pin)

    @staticmethod
    def join(homework, number, nickname, pin):
        """임시 계정을 만들어 자리에 앉힌다. 같은 번호가 동시에 들어오면 한 명만 앉는다."""
        try:
            with transaction.atomic():
                user = User(username=f"{GUEST_USERNAME_PREFIX}{secrets.token_hex(8)}",
                            admin_type=AdminType.GUEST)
                user.set_unusable_password()
                user.save()
                UserProfile.objects.create(user=user)
                return HomeworkParticipant.objects.create(
                    homework=homework, user=user, number=number, nickname=nickname, pin=pin)
        except IntegrityError:
            raise APIError("방금 다른 학생이 그 번호로 들어왔습니다. 번호를 확인해주세요")


@receiver(post_delete, sender=HomeworkParticipant)
def delete_guest_account(sender, instance, **kwargs):
    """참가자가 지워지면(내보내기·과제 삭제) 임시 계정과 그 제출도 지운다."""
    User.objects.filter(id=instance.user_id, admin_type=AdminType.GUEST).delete()


def active_homework_with(problem):
    """이 문제가 담긴 진행 중인 바로 과제. 없으면 None."""
    return Homework.objects.filter(items__problem=problem, ended_at__isnull=True,
                                   end_time__gt=now()).first()
