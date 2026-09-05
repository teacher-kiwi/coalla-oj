"""문제 하나의 제출을 전부 다시 채점한다.

테스트케이스를 잘못 만들어 고쳤을 때 쓴다. 이미 채점된 결과가 새 테스트케이스와
어긋난 채로 남으면 정답률도 대회 순위도 틀린 값이 된다.

한 번에 하나씩 채점한다. 여러 개를 동시에 던지면 순위를 다시 쌓을 때 필요한
순서가 흐트러지고, 채점 서버도 학생 제출과 함께 밀린다. 다시 채점하는 동안에는
통계와 순위를 건드리지 않고, 다 끝난 뒤 judge.recompute 로 한 번에 다시 만든다.
"""
import logging
import time

from submission.models import Submission
from .dispatcher import JudgeDispatcher
from .recompute import rebuild_after_rejudge

logger = logging.getLogger(__name__)

# 빈 채점 서버가 없을 때 기다리는 간격과 횟수. 학생 제출이 몰리는 동안에도
# 결국 자리가 나도록 넉넉히 기다리되, 서버가 죽었을 때 영원히 붙들지는 않는다.
BUSY_WAIT_SECONDS = 5
BUSY_RETRIES = 60


def rejudge_problem(problem, sleep=time.sleep):
    """제출을 하나씩 다시 채점하고 파생된 값을 다시 만든다.

    :return: 다시 채점한 제출 수
    """
    submission_ids = list(Submission.objects.filter(problem=problem)
                          .order_by("create_time", "id").values_list("id", flat=True))
    done = 0
    for submission_id in submission_ids:
        for _ in range(BUSY_RETRIES):
            if JudgeDispatcher(submission_id, problem.id).judge(update_stats=False):
                done += 1
                break
            sleep(BUSY_WAIT_SECONDS)
        else:
            logger.error(f"Rejudge gave up waiting for a judge server, submission {submission_id}")

    rebuild_after_rejudge(problem)
    return done
