import hashlib
import json
import logging
from urllib.parse import urljoin

import requests
from django.db import transaction, IntegrityError
from django.db.models import F

from account.models import User
from conf.models import JudgeServer
from contest.models import ContestRuleType, ACMContestRank, OIContestRank, ContestStatus
from options.options import SysOptions
from problem.models import ContestProblem, Problem, ProblemRuleType
from problem.utils import parse_problem_template
from submission.models import JudgeStatus, Submission
from utils.cache import cache
from utils.constants import CacheKey

logger = logging.getLogger(__name__)


# 대기열에 남은 채점을 이어서 처리한다
def process_pending_task():
    if cache.llen(CacheKey.waiting_queue):
        # 순환 임포트를 피하려고 여기서 가져온다
        from judge.tasks import judge_task
        tmp_data = cache.rpop(CacheKey.waiting_queue)
        if tmp_data:
            data = json.loads(tmp_data.decode("utf-8"))
            judge_task.send(**data)


class ChooseJudgeServer:
    def __init__(self):
        self.server = None

    def __enter__(self) -> [JudgeServer, None]:
        with transaction.atomic():
            servers = JudgeServer.objects.select_for_update().filter(is_disabled=False).order_by("task_number")
            servers = [s for s in servers if s.status == "normal"]
            for server in servers:
                if server.task_number <= server.cpu_core * 2:
                    server.task_number = F("task_number") + 1
                    server.save(update_fields=["task_number"])
                    self.server = server
                    return server
        return None

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.server:
            JudgeServer.objects.filter(id=self.server.id).update(task_number=F("task_number") - 1)


class DispatcherBase(object):
    def __init__(self):
        self.token = hashlib.sha256(SysOptions.judge_server_token.encode("utf-8")).hexdigest()

    def _request(self, url, data=None):
        kwargs = {"headers": {"X-Judge-Server-Token": self.token}}
        if data:
            kwargs["json"] = data
        try:
            return requests.post(url, **kwargs).json()
        except Exception as e:
            logger.exception(e)


class SPJCompiler(DispatcherBase):
    def __init__(self, spj_code, spj_version, spj_language):
        super().__init__()
        spj_compile_config = list(filter(lambda config: spj_language == config["name"], SysOptions.spj_languages))[0]["spj"][
            "compile"]
        self.data = {
            "src": spj_code,
            "spj_version": spj_version,
            "spj_compile_config": spj_compile_config
        }

    def compile_spj(self):
        with ChooseJudgeServer() as server:
            if not server:
                return "사용 가능한 채점 서버가 없습니다"
            result = self._request(urljoin(server.service_url, "compile_spj"), data=self.data)
            if not result:
                return "채점 서버 호출에 실패했습니다"
            if result["err"]:
                return result["data"]


class JudgeDispatcher(DispatcherBase):
    def __init__(self, submission_id, problem_id):
        super().__init__()
        self.submission = Submission.objects.get(id=submission_id)
        self.contest_id = self.submission.contest_id
        self.last_result = self.submission.result if self.submission.info else None

        self.problem = Problem.objects.get(id=problem_id)
        if self.contest_id:
            # 대회에 담긴 문제인지 확인한다. 문제 자체는 대회와 무관하게 존재한다.
            self.contest_problem = (ContestProblem.objects.select_related("contest")
                                    .get(contest_id=self.contest_id, problem_id=problem_id))
            self.contest = self.contest_problem.contest
        else:
            self.contest_problem = None

    def _compute_statistic_info(self, resp_data):
        # 여러 테스트케이스 중 가장 오래 걸리고 가장 많이 쓴 값을 대표로 저장한다
        self.submission.statistic_info["time_cost"] = max([x["cpu_time"] for x in resp_data])
        self.submission.statistic_info["memory_cost"] = max([x["memory"] for x in resp_data])

        # OI 규칙은 테스트케이스 점수를 합산한다
        if self.problem.rule_type == ProblemRuleType.OI:
            score = 0
            try:
                for i in range(len(resp_data)):
                    if resp_data[i]["result"] == JudgeStatus.ACCEPTED:
                        resp_data[i]["score"] = self.problem.test_case_score[i]["score"]
                        score += resp_data[i]["score"]
                    else:
                        resp_data[i]["score"] = 0
            except IndexError:
                logger.error(f"Index Error raised when summing up the score in problem {self.problem.id}")
                self.submission.statistic_info["score"] = 0
                return
            self.submission.statistic_info["score"] = score

    def judge(self, update_stats=True):
        """채점하고 결과를 저장한다.

        update_stats=False 는 여러 제출을 한꺼번에 다시 채점할 때 쓴다. 통계와
        순위를 하나씩 고치면 제출 순서에 따라 값이 어긋나므로, 결과만 저장해두고
        다 끝난 뒤에 judge.recompute 로 한 번에 다시 만든다.

        :return: 채점했으면 True. 빈 채점 서버가 없어 못 했으면 False.
        """
        language = self.submission.language
        # Block Coding은 Python3로 채점
        if language == "Block Coding":
            language = "Python3"
        sub_config = next((item for item in SysOptions.languages if item["name"] == language), None)
        if sub_config is None:
            # 언어 설정이 시스템에서 제거된 경우. 여기서 예외가 나면 태스크가 죽고
            # 제출은 영원히 Pending 으로 남으므로 상태를 명시적으로 정리한다.
            logger.error(f"Language {language} is not configured, submission id: {self.submission.id}")
            self.submission.result = JudgeStatus.SYSTEM_ERROR
            self.submission.statistic_info["err_info"] = f"언어 {language} 의 설정이 없습니다"
            self.submission.statistic_info["score"] = 0
            self.submission.save()
            return True
        spj_config = {}
        if self.problem.spj_code:
            for lang in SysOptions.spj_languages:
                if lang["name"] == self.problem.spj_language:
                    spj_config = lang["spj"]
                    break

        if language in self.problem.template:
            template = parse_problem_template(self.problem.template[language])
            code = "\n".join([template["prepend"], self.submission.code, template["append"]])
        else:
            code = self.submission.code

        data = {
            "language_config": sub_config["config"],
            "src": code,
            "max_cpu_time": self.problem.time_limit,
            "max_memory": 1024 * 1024 * self.problem.memory_limit,
            "test_case_id": self.problem.test_case_id,
            "output": False,
            "spj_version": self.problem.spj_version,
            "spj_config": spj_config.get("config"),
            "spj_compile_config": spj_config.get("compile"),
            "spj_src": self.problem.spj_code,
            "io_mode": self.problem.io_mode
        }

        with ChooseJudgeServer() as server:
            if not server:
                if not update_stats:
                    # 한꺼번에 다시 채점하는 중이다. 대기열에 넣으면 나중에 통계를
                    # 올리며 채점되어 두 번 세어진다. 부른 쪽이 다시 시도한다.
                    return False
                data = {"submission_id": self.submission.id, "problem_id": self.problem.id}
                cache.lpush(CacheKey.waiting_queue, json.dumps(data))
                return True
            Submission.objects.filter(id=self.submission.id).update(result=JudgeStatus.JUDGING)
            resp = self._request(urljoin(server.service_url, "/judge"), data=data)

        if not resp:
            Submission.objects.filter(id=self.submission.id).update(result=JudgeStatus.SYSTEM_ERROR)
            return True

        if resp["err"]:
            self.submission.result = JudgeStatus.COMPILE_ERROR
            self.submission.statistic_info["err_info"] = resp["data"]
            self.submission.statistic_info["score"] = 0
        else:
            resp["data"].sort(key=lambda x: int(x["test_case"]))
            self.submission.info = resp
            self._compute_statistic_info(resp["data"])
            error_test_case = list(filter(lambda case: case["result"] != 0, resp["data"]))
            # ACM: 전부 맞으면 AC, 아니면 처음 틀린 테스트케이스의 결과를 쓴다
            # OI: 전부 맞으면 AC, 전부 틀리면 처음 틀린 결과, 그 사이면 부분 점수
            if not error_test_case:
                self.submission.result = JudgeStatus.ACCEPTED
            elif self.problem.rule_type == ProblemRuleType.ACM or len(error_test_case) == len(resp["data"]):
                self.submission.result = error_test_case[0]["result"]
            else:
                self.submission.result = JudgeStatus.PARTIALLY_ACCEPTED
        self.submission.save()

        if not update_stats:
            return True

        if self.contest_id:
            if self.contest.status != ContestStatus.CONTEST_UNDERWAY or \
                    User.objects.get(id=self.submission.user_id).is_contest_admin(self.contest):
                logger.info(
                    "Contest debug mode, id: " + str(self.contest_id) + ", submission id: " + self.submission.id)
                return True
            with transaction.atomic():
                self.update_contest_problem_status()
                self.update_contest_rank()
        else:
            if self.last_result:
                self.update_problem_status_rejudge()
            else:
                self.update_problem_status()

        # 채점이 끝났으니 대기열에 남은 것을 이어서 처리한다
        process_pending_task()
        return True

    def update_problem_status_rejudge(self):
        result = str(self.submission.result)
        # statistic_info 는 JSON 이라 키가 항상 문자열이다. 예전에는 int 인
        # self.last_result 로 조회해서 항상 빗나갔고, 그 결과 이전 결과의 횟수가
        # 실제 값과 무관하게 0 이 되었다(오답 5회 -> 재채점 한 번에 0회).
        last_result = str(self.last_result)
        problem_id = str(self.problem.id)
        with transaction.atomic():
            problem = Problem.objects.select_for_update().get(id=self.problem.id)
            if self.last_result != JudgeStatus.ACCEPTED and self.submission.result == JudgeStatus.ACCEPTED:
                problem.accepted_number += 1
            problem_info = problem.statistic_info
            problem_info[last_result] = max(problem_info.get(last_result, 1) - 1, 0)
            problem_info[result] = problem_info.get(result, 0) + 1
            problem.save(update_fields=["accepted_number", "statistic_info"])

            profile = User.objects.select_for_update().get(id=self.submission.user_id).userprofile
            if problem.rule_type == ProblemRuleType.ACM:
                acm_problems_status = profile.acm_problems_status.get("problems", {})
                if acm_problems_status[problem_id]["status"] != JudgeStatus.ACCEPTED:
                    acm_problems_status[problem_id]["status"] = self.submission.result
                    if self.submission.result == JudgeStatus.ACCEPTED:
                        profile.accepted_number += 1
                profile.acm_problems_status["problems"] = acm_problems_status
                profile.save(update_fields=["accepted_number", "acm_problems_status"])

            else:
                oi_problems_status = profile.oi_problems_status.get("problems", {})
                score = self.submission.statistic_info["score"]
                if oi_problems_status[problem_id]["status"] != JudgeStatus.ACCEPTED:
                    # 지난번 점수를 빼고 이번 점수를 더한다
                    profile.add_score(this_time_score=score,
                                      last_time_score=oi_problems_status[problem_id]["score"])
                    oi_problems_status[problem_id]["score"] = score
                    oi_problems_status[problem_id]["status"] = self.submission.result
                    if self.submission.result == JudgeStatus.ACCEPTED:
                        profile.accepted_number += 1
                profile.oi_problems_status["problems"] = oi_problems_status
                profile.save(update_fields=["accepted_number", "oi_problems_status"])

    def _update_solved_problems(self, user_profile, rule_type):
        """프로필의 "푼 문제" 표시와 점수를 갱신한다.

        대회 제출도 여기를 지난다. 대회에서 푼 것도 그 문제를 푼 것이고, 문제
        통계(정답률)도 이미 대회 제출을 함께 세고 있어서 여기만 빼두면 어긋난다.
        제출 목록에 남에게 보이는 시점만 대회가 끝난 뒤로 미룬다(그쪽은 공정성 문제다).
        """
        problem_id = str(self.problem.id)
        accepted = self.submission.result == JudgeStatus.ACCEPTED
        user_profile.submission_number += 1
        if rule_type == ProblemRuleType.ACM:
            solved = user_profile.acm_problems_status.get("problems", {})
            if problem_id not in solved:
                solved[problem_id] = {"status": self.submission.result}
                if accepted:
                    user_profile.accepted_number += 1
            elif solved[problem_id]["status"] != JudgeStatus.ACCEPTED:
                solved[problem_id]["status"] = self.submission.result
                if accepted:
                    user_profile.accepted_number += 1
            user_profile.acm_problems_status["problems"] = solved
            user_profile.save(update_fields=["submission_number", "accepted_number",
                                             "acm_problems_status"])
        else:
            solved = user_profile.oi_problems_status.get("problems", {})
            score = self.submission.statistic_info["score"]
            if problem_id not in solved:
                user_profile.add_score(score)
                solved[problem_id] = {"status": self.submission.result, "score": score}
                if accepted:
                    user_profile.accepted_number += 1
            elif solved[problem_id]["status"] != JudgeStatus.ACCEPTED:
                # 지난번 점수를 빼고 이번 점수를 더한다
                user_profile.add_score(this_time_score=score,
                                       last_time_score=solved[problem_id]["score"])
                solved[problem_id]["score"] = score
                solved[problem_id]["status"] = self.submission.result
                if accepted:
                    user_profile.accepted_number += 1
            user_profile.oi_problems_status["problems"] = solved
            user_profile.save(update_fields=["submission_number", "accepted_number",
                                             "oi_problems_status"])

    def update_problem_status(self):
        result = str(self.submission.result)
        with transaction.atomic():
            problem = Problem.objects.select_for_update().get(id=self.problem.id)
            problem.submission_number += 1
            if self.submission.result == JudgeStatus.ACCEPTED:
                problem.accepted_number += 1
            problem_info = problem.statistic_info
            problem_info[result] = problem_info.get(result, 0) + 1
            problem.save(update_fields=["accepted_number", "submission_number", "statistic_info"])

            user = User.objects.select_for_update().get(id=self.submission.user_id)
            self._update_solved_problems(user.userprofile, problem.rule_type)

    def update_contest_problem_status(self):
        with transaction.atomic():
            user = User.objects.select_for_update().get(id=self.submission.user_id)
            user_profile = user.userprofile
            problem_id = str(self.problem.id)
            # 대회별로 나눠 담는다. 한 문제를 여러 대회에 담을 수 있게 되면서
            # 문제 id 만으로 담으면 대회 A 에서 푼 것이 대회 B 에서도 풀린 것으로 보인다.
            contest_id = str(self.contest_id)
            if self.contest.rule_type == ContestRuleType.ACM:
                by_contest = user_profile.acm_problems_status.get("contest_problems", {})
                contest_problems_status = by_contest.setdefault(contest_id, {})
                if problem_id not in contest_problems_status:
                    contest_problems_status[problem_id] = {"status": self.submission.result}
                elif contest_problems_status[problem_id]["status"] != JudgeStatus.ACCEPTED:
                    contest_problems_status[problem_id]["status"] = self.submission.result
                else:
                    # 이미 AC 라면 어떤 카운터도 건드리지 않는다
                    return
                user_profile.acm_problems_status["contest_problems"] = by_contest
                user_profile.save(update_fields=["acm_problems_status"])

            elif self.contest.rule_type == ContestRuleType.OI:
                by_contest = user_profile.oi_problems_status.get("contest_problems", {})
                contest_problems_status = by_contest.setdefault(contest_id, {})
                score = self.submission.statistic_info["score"]
                if problem_id not in contest_problems_status:
                    contest_problems_status[problem_id] = {"status": self.submission.result,
                                                           "score": score}
                else:
                    contest_problems_status[problem_id]["score"] = score
                    contest_problems_status[problem_id]["status"] = self.submission.result
                user_profile.oi_problems_status["contest_problems"] = by_contest
                user_profile.save(update_fields=["oi_problems_status"])

            result = str(self.submission.result)
            accepted = self.submission.result == JudgeStatus.ACCEPTED
            # 대회 안 통계. 대회 화면이 이것을 보여준다.
            entry = ContestProblem.objects.select_for_update().get(id=self.contest_problem.id)
            entry.statistic_info[result] = entry.statistic_info.get(result, 0) + 1
            entry.submission_number += 1
            if accepted:
                entry.accepted_number += 1
            entry.save(update_fields=["submission_number", "accepted_number", "statistic_info"])

            # 문제 자체의 누적. 대회가 끝나고 문제를 공개로 돌리면 이 값이 보인다.
            problem = Problem.objects.select_for_update().get(id=self.problem.id)
            problem.statistic_info[result] = problem.statistic_info.get(result, 0) + 1
            problem.submission_number += 1
            if accepted:
                problem.accepted_number += 1
            problem.save(update_fields=["submission_number", "accepted_number", "statistic_info"])

            # 문제 목록의 "푼 문제" 표시. 대회에서 푼 것도 그 문제를 푼 것이다.
            self._update_solved_problems(user_profile, problem.rule_type)

    def update_contest_rank(self):
        if self.contest.rule_type == ContestRuleType.OI or self.contest.real_time_rank:
            cache.delete(f"{CacheKey.contest_rank_cache}:{self.contest.id}")

        def get_rank(model):
            return model.objects.select_for_update().get(user_id=self.submission.user_id, contest=self.contest)

        if self.contest.rule_type == ContestRuleType.ACM:
            model = ACMContestRank
            func = self._update_acm_contest_rank
        else:
            model = OIContestRank
            func = self._update_oi_contest_rank

        try:
            rank = get_rank(model)
        except model.DoesNotExist:
            try:
                model.objects.create(user_id=self.submission.user_id, contest=self.contest)
                rank = get_rank(model)
            except IntegrityError:
                rank = get_rank(model)
        func(rank)

    def _update_acm_contest_rank(self, rank):
        info = rank.submission_info.get(str(self.submission.problem_id))
        # 앞에서 값을 바꿨으므로 다시 읽어온다. 최초 정답은 대회 안 정답 수로 본다
        # (문제 자체의 누적을 보면 예전에 공개로 풀린 것까지 세어 아무도 최초가 못 된다).
        problem = ContestProblem.objects.select_for_update().get(id=self.contest_problem.id)
        # 이 문제를 이미 제출한 적이 있다
        if info:
            if info["is_ac"]:
                return

            rank.submission_number += 1
            if self.submission.result == JudgeStatus.ACCEPTED:
                rank.accepted_number += 1
                info["is_ac"] = True
                info["ac_time"] = (self.submission.create_time - self.contest.start_time).total_seconds()
                rank.total_time += info["ac_time"] + info["error_number"] * 20 * 60

                if problem.accepted_number == 1:
                    info["is_first_ac"] = True
            elif self.submission.result != JudgeStatus.COMPILE_ERROR:
                info["error_number"] += 1

        # 이 문제의 첫 제출
        else:
            rank.submission_number += 1
            info = {"is_ac": False, "ac_time": 0, "error_number": 0, "is_first_ac": False}
            if self.submission.result == JudgeStatus.ACCEPTED:
                rank.accepted_number += 1
                info["is_ac"] = True
                info["ac_time"] = (self.submission.create_time - self.contest.start_time).total_seconds()
                rank.total_time += info["ac_time"]

                if problem.accepted_number == 1:
                    info["is_first_ac"] = True

            elif self.submission.result != JudgeStatus.COMPILE_ERROR:
                info["error_number"] = 1
        rank.submission_info[str(self.submission.problem_id)] = info
        rank.save()

    def _update_oi_contest_rank(self, rank):
        problem_id = str(self.submission.problem_id)
        current_score = self.submission.statistic_info["score"]
        last_score = rank.submission_info.get(problem_id)
        if last_score:
            rank.total_score = rank.total_score - last_score + current_score
        else:
            rank.total_score = rank.total_score + current_score
        rank.submission_info[problem_id] = current_score
        rank.save()
