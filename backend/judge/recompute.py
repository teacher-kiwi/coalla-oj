"""집계를 제출 기록에서 처음부터 다시 만든다.

테스트케이스를 고치면 이미 채점된 제출의 결과가 실제와 어긋난다. 그래서 다시
채점해야 하는데, 결과만 고치면 그 결과에서 파생된 값들(문제 정답률, 대회 순위,
"푼 문제" 표시)이 옛날 그대로 남는다. 특히 대회 순위는 제출 순서에 따라 패널티가
쌓이는 값이라 하나씩 되돌릴 수 없다.

그래서 되돌리지 않고 다시 만든다. 채점 결과만 고쳐 놓고, 파생된 값은 비운 뒤
제출을 시간 순으로 다시 훑어 쌓는다. 규칙은 채점 직후에 쓰는 것(JudgeDispatcher)과
같다.

한 가지는 일부러 다르게 본다. 채점 직후에는 "지금 대회가 진행 중인가"로 대회
제출인지 판단하는데, 다시 만드는 시점에는 그 대회가 이미 끝나 있다. 대신 "제출한
시각이 대회 시간 안이었는가"를 본다. 원래 뜻에 더 가깝고, 제출 목록이 대회 제출을
고르는 기준과도 같다.
"""
from django.db import transaction
from django.db.models import F, Q

from account.models import AdminType, User, UserProfile
from contest.models import ACMContestRank, Contest, ContestRuleType, OIContestRank
from problem.models import ContestProblem, Problem, ProblemRuleType
from submission.models import JudgeStatus, Submission
from utils.cache import cache
from utils.constants import CacheKey

# ACM 규칙에서 오답 한 번에 붙는 시간 손해
PENALTY_SECONDS = 20 * 60


def _is_debug_submission(submission, contest):
    """집계에 넣지 않는 제출인지.

    대회 관리자(출제자·최고관리자)가 자기 대회에 넣어보는 시험 제출과, 대회 시간
    밖의 제출은 순위에도 통계에도 넣지 않는다(채점 직후 규칙과 같다).
    """
    if contest is None:
        return False
    if submission.user.is_contest_admin(contest):
        return True
    return not (contest.start_time <= submission.create_time <= contest.end_time)


def _counted_submissions(problem):
    """이 문제의 제출 중 집계에 넣을 것만, 시간 순으로."""
    submissions = (Submission.objects.filter(problem=problem)
                   .select_related("contest", "user")
                   .order_by("create_time", "id"))
    for submission in submissions:
        contest = submission.contest
        if not _is_debug_submission(submission, contest):
            yield submission, contest


def _counted_submission_filter(user):
    """이 사용자의 제출 중 집계에 넣을 것을 고르는 조건.

    최고관리자는 어느 대회에서도 관리자라 대회 제출이 전부 시험 제출이다.
    나머지는 자기가 연 대회에서만 그렇다.
    """
    if user.admin_type == AdminType.SUPER_ADMIN:
        return Q(contest__isnull=True)
    return Q(contest__isnull=True) | (Q(contest__start_time__lte=F("create_time"))
                                      & Q(contest__end_time__gte=F("create_time"))
                                      & ~Q(contest__created_by_id=user.id))


def _blank_counters():
    return {"submission_number": 0, "accepted_number": 0, "statistic_info": {}}


def _count(counters, result):
    counters["submission_number"] += 1
    if result == JudgeStatus.ACCEPTED:
        counters["accepted_number"] += 1
    key = str(result)
    counters["statistic_info"][key] = counters["statistic_info"].get(key, 0) + 1


@transaction.atomic
def _add_counters(into, other):
    """other 의 몫을 into 에 더한다."""
    into["submission_number"] += other["submission_number"]
    into["accepted_number"] += other["accepted_number"]
    for key, value in other["statistic_info"].items():
        into["statistic_info"][key] = into["statistic_info"].get(key, 0) + value
    return into


def preserve_statistics(submissions):
    """지워질 제출의 몫을 문제의 보존 칸으로 옮긴다.

    제출을 지우기 **전에** 불러야 한다. 지운 뒤에는 셀 근거가 없다.
    이렇게 옮겨 두어야 나중에 그 문제를 재채점해도 지워진 학생들의 몫이 남는다.

    대회별 통계(ContestProblem)는 보존하지 않는다. 학생이 지워지면 그 대회의
    순위 행도 함께 사라지므로, 대회 화면은 남아 있는 제출만 보여주는 쪽이 맞다.
    """
    by_problem = {}
    for submission in submissions.select_related("contest", "user"):
        if _is_debug_submission(submission, submission.contest):
            continue
        _count(by_problem.setdefault(submission.problem_id, _blank_counters()),
               submission.result)

    for problem in Problem.objects.filter(id__in=by_problem).only(
            "id", "archived_submission_number", "archived_accepted_number",
            "archived_statistic_info"):
        counters = _add_counters({
            "submission_number": problem.archived_submission_number,
            "accepted_number": problem.archived_accepted_number,
            "statistic_info": dict(problem.archived_statistic_info or {}),
        }, by_problem[problem.id])
        Problem.objects.filter(id=problem.id).update(
            archived_submission_number=counters["submission_number"],
            archived_accepted_number=counters["accepted_number"],
            archived_statistic_info=counters["statistic_info"])


def rebuild_problem_statistics(problem):
    """문제와 대회별 통계를 다시 센다.

    문제 자체는 평생 누적이라 대회 제출까지 함께 세고, 대회별 통계는 그 대회
    제출만 센다(대회 화면에 예전에 공개로 풀린 횟수가 나오면 난이도가 샌다).

    문제의 값에는 지워진 학생들의 몫(archived_*)을 함께 더한다. 살아 있는
    제출만 세면 학급을 지운 뒤 재채점하는 순간 예전 기록이 사라진다.
    """
    total = _blank_counters()
    per_contest = {entry.contest_id: _blank_counters()
                   for entry in ContestProblem.objects.filter(problem=problem)}

    for submission, contest in _counted_submissions(problem):
        _count(total, submission.result)
        if contest is not None and contest.id in per_contest:
            _count(per_contest[contest.id], submission.result)

    # 넘겨받은 인스턴스가 오래됐을 수 있어 보존 칸은 DB 에서 다시 읽는다
    archived = Problem.objects.filter(id=problem.id).values(
        "archived_submission_number", "archived_accepted_number",
        "archived_statistic_info").first() or {}
    _add_counters(total, {
        "submission_number": archived.get("archived_submission_number", 0),
        "accepted_number": archived.get("archived_accepted_number", 0),
        "statistic_info": archived.get("archived_statistic_info") or {},
    })
    Problem.objects.filter(id=problem.id).update(**total)
    for contest_id, counters in per_contest.items():
        ContestProblem.objects.filter(problem=problem, contest_id=contest_id).update(**counters)


def _acm_ranks(contest, submissions):
    """ICPC 규칙으로 순위를 쌓는다.

    한 문제를 맞히면 그 뒤 제출은 세지 않는다. 맞히기까지 걸린 시간에 그때까지
    틀린 횟수만큼 패널티를 더한다. 컴파일 에러는 틀린 것으로 세지 않는다.
    """
    ranks = {}
    first_ac_done = set()
    for submission in submissions:
        rank = ranks.setdefault(submission.user_id,
                                {"submission_number": 0, "accepted_number": 0,
                                 "total_time": 0, "submission_info": {}})
        problem_key = str(submission.problem_id)
        info = rank["submission_info"].setdefault(
            problem_key, {"is_ac": False, "ac_time": 0, "error_number": 0, "is_first_ac": False})
        if info["is_ac"]:
            continue

        rank["submission_number"] += 1
        if submission.result == JudgeStatus.ACCEPTED:
            rank["accepted_number"] += 1
            info["is_ac"] = True
            info["ac_time"] = (submission.create_time - contest.start_time).total_seconds()
            rank["total_time"] += info["ac_time"] + info["error_number"] * PENALTY_SECONDS
            if problem_key not in first_ac_done:
                info["is_first_ac"] = True
                first_ac_done.add(problem_key)
        elif submission.result != JudgeStatus.COMPILE_ERROR:
            info["error_number"] += 1
    return ranks


def _oi_ranks(submissions):
    """OI 규칙. 문제마다 마지막 제출의 점수를 쓰고 전부 더한다."""
    ranks = {}
    for submission in submissions:
        rank = ranks.setdefault(submission.user_id,
                                {"submission_number": 0, "submission_info": {}})
        rank["submission_number"] += 1
        rank["submission_info"][str(submission.problem_id)] = \
            submission.statistic_info.get("score", 0)
    for rank in ranks.values():
        rank["total_score"] = sum(rank["submission_info"].values())
    return ranks


@transaction.atomic
def rebuild_contest_rank(contest):
    """대회 순위표를 제출 기록에서 다시 만든다.

    순위는 제출 순서에 따라 패널티가 쌓이는 값이라 제출 하나만 되돌릴 수 없다.
    통째로 지우고 다시 쌓는다.
    """
    submissions = [
        s for s in (Submission.objects.filter(contest=contest,
                                              create_time__gte=contest.start_time,
                                              create_time__lte=contest.end_time)
                    .select_related("user").order_by("create_time", "id"))
        if not s.user.is_contest_admin(contest)
    ]

    if contest.rule_type == ContestRuleType.ACM:
        model, ranks = ACMContestRank, _acm_ranks(contest, submissions)
    else:
        model, ranks = OIContestRank, _oi_ranks(submissions)

    model.objects.filter(contest=contest).delete()
    model.objects.bulk_create([model(contest=contest, user_id=user_id, **fields)
                               for user_id, fields in ranks.items()])
    cache.delete(f"{CacheKey.contest_rank_cache}:{contest.id}")


def _replay_solved(problem):
    """이 문제를 사용자별로 다시 훑어 "푼 문제" 표시를 만든다."""
    replay = {}
    for submission, _ in _counted_submissions(problem):
        entry = replay.setdefault(submission.user_id, {"status": None, "score": 0})
        # 한 번 맞힌 뒤에는 상태가 바뀌지 않는다(채점 직후 규칙과 같다)
        if entry["status"] != JudgeStatus.ACCEPTED:
            entry["status"] = submission.result
            entry["score"] = submission.statistic_info.get("score", 0)
    return replay


@transaction.atomic
def rebuild_solved_status(problem):
    """이 문제의 "푼 문제" 표시를 고치고, 딸린 프로필 숫자를 다시 센다.

    정답 수·점수·제출 수는 다른 문제 몫이 섞여 있는 값이라 차이만큼 빼고 더하면
    한 번이라도 어긋났을 때 영영 어긋난 채로 남는다. 표시를 고친 뒤 프로필에서
    통째로 다시 센다.
    """
    problem_key = str(problem.id)
    field = ("oi_problems_status" if problem.rule_type == ProblemRuleType.OI
             else "acm_problems_status")
    replay = _replay_solved(problem)

    # 제출이 사라져 표시만 남은 사람까지 걷어내려고 지금 표시된 사람도 함께 본다
    marked = {profile.user_id for profile in UserProfile.objects.only("user_id", field)
              if problem_key in getattr(profile, field).get("problems", {})}

    for user in User.objects.filter(id__in=set(replay) | marked).select_related("userprofile"):
        profile = user.userprofile
        status = getattr(profile, field)
        solved = status.get("problems", {})
        entry = replay.get(user.id)
        if entry is None:
            solved.pop(problem_key, None)
        elif problem.rule_type == ProblemRuleType.OI:
            solved[problem_key] = {"status": entry["status"], "score": entry["score"]}
        else:
            solved[problem_key] = {"status": entry["status"]}
        status["problems"] = solved
        setattr(profile, field, status)
        _recount_profile(profile, user)


def _recount_profile(profile, user):
    """프로필의 정답 수·점수·제출 수를 표시와 제출 기록에서 다시 센다."""
    acm_solved = profile.acm_problems_status.get("problems", {})
    oi_solved = profile.oi_problems_status.get("problems", {})
    profile.accepted_number = sum(
        1 for solved in (acm_solved, oi_solved) for entry in solved.values()
        if entry.get("status") == JudgeStatus.ACCEPTED)
    profile.total_score = sum(entry.get("score", 0) for entry in oi_solved.values())
    profile.submission_number = (Submission.objects.filter(user_id=user.id)
                                 .filter(_counted_submission_filter(user)).count())
    profile.save(update_fields=["accepted_number", "total_score", "submission_number",
                                "acm_problems_status", "oi_problems_status"])


def rebuild_after_rejudge(problem):
    """다시 채점한 뒤 파생된 값을 전부 다시 만든다."""
    rebuild_problem_statistics(problem)
    rebuild_solved_status(problem)
    for contest in Contest.objects.filter(problems__problem=problem).distinct():
        rebuild_contest_rank(contest)
