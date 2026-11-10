"""코인 제도를 시작하기 전에 푼 연습 문제에도 정답 코인을 준다(한 번만 돌리면 된다).

푼 기록(acm/oi_problems_status 의 "problems")을 보고 문제마다 10코인을 준다.
대회 안에서만 푼 문제는 "contest_problems" 에 따로 있어서 빠진다.
원장이 (사용자, 이유, 문제)로 겹치지 않으니 여러 번 돌려도 두 번 주지 않는다.

    python manage.py grant_past_solve_coins           # 얼마나 줄지 보기만
    python manage.py grant_past_solve_coins --apply   # 실제로 주기
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from account.models import AdminType, UserProfile
from avatar.coins import SOLVE_COINS
from avatar.models import CoinLog, CoinReason
from submission.models import JudgeStatus


class Command(BaseCommand):
    help = "코인 제도 전에 푼 연습 문제에 정답 코인을 준다"

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="실제로 준다(없으면 보기만)")

    def handle(self, *args, **options):
        have = set(CoinLog.objects.filter(reason=CoinReason.SOLVE).values_list("user_id", "ref"))
        new = []
        for profile in UserProfile.objects.select_related("user").exclude(user__admin_type=AdminType.GUEST):
            solved = set()
            for status in (profile.acm_problems_status, profile.oi_problems_status):
                for pid, info in (status or {}).get("problems", {}).items():
                    if info.get("status") == JudgeStatus.ACCEPTED:
                        solved.add(str(pid))
            for pid in sorted(solved, key=int):
                if (profile.user_id, pid) not in have:
                    new.append(CoinLog(user_id=profile.user_id, reason=CoinReason.SOLVE, ref=pid,
                                       amount=SOLVE_COINS))
        users = {}
        for log in new:
            users[log.user_id] = users.get(log.user_id, 0) + log.amount
        self.stdout.write(f"사용자 {len(users)}명, {len(new)}문제, 모두 {sum(users.values())}코인")
        if not options["apply"]:
            self.stdout.write("보기만 했습니다. 주려면 --apply 를 붙이세요.")
            return
        with transaction.atomic():
            CoinLog.objects.bulk_create(new, ignore_conflicts=True)
        self.stdout.write("주었습니다.")
