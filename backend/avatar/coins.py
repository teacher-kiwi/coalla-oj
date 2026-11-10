"""코인 주기와 잔액. 2026-11 결정: 연습 문제 처음 정답 10, 하루 출석 5. 대회 정답은 주지 않는다."""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from django.db import IntegrityError, transaction
from django.db.models import Sum

from account.models import AdminType

from .models import CoinLog, CoinReason

logger = logging.getLogger(__name__)

SOLVE_COINS = 10
ATTEND_COINS = 5
KST = ZoneInfo("Asia/Seoul")


def balance(user_id):
    return CoinLog.objects.filter(user_id=user_id).aggregate(s=Sum("amount"))["s"] or 0


def _earns(user):
    # 바로 과제의 임시 계정은 과제가 끝나면 사라지고 캐릭터도 없다
    return user is not None and user.admin_type != AdminType.GUEST


def _grant(user_id, reason, ref, amount, submission_id=""):
    """한 번만 준다. 새로 줬으면 금액, 이미 받았으면 0."""
    try:
        with transaction.atomic():
            CoinLog.objects.create(user_id=user_id, reason=reason, ref=str(ref), amount=amount,
                                   submission_id=submission_id or "")
        return amount
    except IntegrityError:
        return 0


def grant_solve(submission, user):
    """연습 문제(대회 밖)를 처음 맞혔을 때. 채점 쪽에서 부른다. 실패해도 채점은 계속된다."""
    if submission.contest_id or not _earns(user):
        return 0
    try:
        return _grant(user.id, CoinReason.SOLVE, submission.problem_id, SOLVE_COINS, submission.id)
    except Exception:
        logger.exception("solve coin failed, submission %s", submission.id)
        return 0


def today():
    return datetime.now(KST).date().isoformat()


def grant_attendance(user):
    """그날(한국 날짜) 처음 들어왔을 때 5코인. 새로 줬으면 금액, 아니면 0."""
    if not _earns(user):
        return 0
    return _grant(user.id, CoinReason.ATTEND, today(), ATTEND_COINS)
