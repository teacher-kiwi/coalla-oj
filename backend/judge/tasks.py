import logging

import dramatiq

from account.models import User
from problem.models import Problem
from submission.models import Submission
from judge.dispatcher import JudgeDispatcher
from judge.rejudge import rejudge_problem
from judge.verify import run_verification
from utils.shortcuts import DRAMATIQ_WORKER_ARGS

logger = logging.getLogger(__name__)

# 워커는 "tasks" 라는 이름의 모듈만 훑어 액터를 찾는다
# (django_dramatiq 의 DRAMATIQ_AUTODISCOVER_MODULES 기본값).
# 다른 파일에 두면 등록되지 않아 보낸 작업이 ActorNotFound 로 버려진다.


@dramatiq.actor(**DRAMATIQ_WORKER_ARGS())
def judge_task(submission_id, problem_id):
    uid = Submission.objects.get(id=submission_id).user_id
    if User.objects.get(id=uid).is_disabled:
        return
    JudgeDispatcher(submission_id, problem_id).judge()


@dramatiq.actor(**DRAMATIQ_WORKER_ARGS())
def verify_solution_task(token, spec):
    """정답 코드로 테스트케이스를 확인한다.

    저장과 분리돼 있어 사람을 기다리게 하지 않는다. 채점 서버가 바쁘면
    자리가 날 때까지 기다렸다가 돌고, 결과는 표(token)로 찾아간다.
    문제를 저장하기 전에도 돌리므로 결과를 문제가 아니라 캐시에 둔다.
    """
    passed, message = run_verification(token, spec)
    logger.info(f"Verification {token}: passed={passed} ({message})")


@dramatiq.actor(**DRAMATIQ_WORKER_ARGS())
def rejudge_problem_task(problem_id):
    problem = Problem.objects.filter(id=problem_id).first()
    if problem is None:
        return
    count = rejudge_problem(problem)
    logger.info(f"Rejudged {count} submissions of problem {problem_id}")
