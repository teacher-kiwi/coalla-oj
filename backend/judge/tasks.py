import logging

import dramatiq

from account.models import User
from problem.models import Problem
from submission.models import Submission
from judge.dispatcher import JudgeDispatcher
from judge.rejudge import rejudge_problem
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
def rejudge_problem_task(problem_id):
    problem = Problem.objects.filter(id=problem_id).first()
    if problem is None:
        return
    count = rejudge_problem(problem)
    logger.info(f"Rejudged {count} submissions of problem {problem_id}")
