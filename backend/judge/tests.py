"""채점 결과를 통계·프로필에 반영하는 부분(JudgeDispatcher)을 검증한다.

여기가 틀리면 학생의 "푼 문제 수"와 문제 정답률이 조용히 어긋난다. 화면에는
아무 오류도 나지 않아 한참 뒤에야 드러나므로 테스트로 고정해둔다.

채점 서버를 부르는 부분(judge())은 건드리지 않고, 서버가 돌려준 결과를 받은
뒤의 처리만 직접 호출한다.
"""
from copy import deepcopy

from account.models import User
from problem.models import Problem, ProblemRuleType, ProblemTag
from submission.models import JudgeStatus, Submission
from utils.api.tests import APITestCase

from .dispatcher import JudgeDispatcher

DEFAULT_PROBLEM_DATA = {
    "_id": "D-1", "title": "test", "description": "<p>test</p>",
    "input_description": "test", "output_description": "test",
    "time_limit": 1000, "memory_limit": 256, "difficulty": "Low",
    "visible": True, "languages": ["C", "Python3"], "template": {},
    "samples": [{"input": "test", "output": "test"}],
    "spj": False, "spj_language": None, "spj_code": None,
    "test_case_id": "d41d8cd98f00b204e9800998ecf8427e",
    "test_case_score": [{"output_name": "1.out", "input_name": "1.in", "score": 40},
                        {"output_name": "2.out", "input_name": "2.in", "score": 60}],
    "rule_type": ProblemRuleType.ACM, "hint": "", "source": "test",
    "io_mode": {"io_mode": "Standard IO", "input": "input.txt", "output": "output.txt"},
}


# 채점 서버가 돌려주는 테스트케이스별 결과의 최소 형태
def case(result, cpu_time=10, memory=1024):
    return {"result": result, "cpu_time": cpu_time, "real_time": cpu_time * 2,
            "memory": memory, "test_case": "1", "output_md5": None,
            "error": 0, "signal": 0}


class DispatcherTestBase(APITestCase):
    def setUp(self):
        self.user = self.create_user("student", "pass123", login=False)
        ProblemTag.objects.create(name="test")
        self.problem = self._create_problem()

    def _create_problem(self, **overrides):
        data = deepcopy(DEFAULT_PROBLEM_DATA)
        data.update(overrides)
        data["created_by"] = self.user
        return Problem.objects.create(**data)

    def _submit(self, result=JudgeStatus.PENDING, info=None, statistic_info=None):
        return Submission.objects.create(user_id=self.user.id, problem_id=self.problem.id,
                                         code="print(1)", language="Python3",
                                         result=result, info=info or {},
                                         statistic_info=statistic_info or {})

    def _dispatcher(self, submission, result):
        """채점이 끝나 결과가 정해진 상태를 만든다"""
        submission.result = result
        submission.save()
        return JudgeDispatcher(submission.id, self.problem.id)

    def _rejudge_dispatcher(self, submission, new_result):
        """재채점 상황을 만든다.

        실제 흐름은 "이전 결과가 남아 있는 상태에서 디스패처를 만들고, 채점이 끝난 뒤
        새 결과를 넣는" 순서다. 디스패처는 생성 시점의 결과를 last_result 로 기억하므로
        순서를 지켜야 한다.
        """
        submission.info = {"err": None, "data": []}
        submission.save()
        dispatcher = JudgeDispatcher(submission.id, self.problem.id)
        dispatcher.submission.result = new_result
        dispatcher.submission.save()
        return dispatcher

    def _profile(self):
        return User.objects.get(id=self.user.id).userprofile


class StatisticInfoTest(DispatcherTestBase):
    def test_time_and_memory_take_the_worst_case(self):
        # 여러 테스트케이스 중 가장 오래 걸리고 가장 많이 쓴 값을 대표로 남긴다
        submission = self._submit()
        dispatcher = self._dispatcher(submission, JudgeStatus.ACCEPTED)
        dispatcher._compute_statistic_info([
            case(JudgeStatus.ACCEPTED, cpu_time=10, memory=1024),
            case(JudgeStatus.ACCEPTED, cpu_time=35, memory=2048),
        ])
        self.assertEqual(dispatcher.submission.statistic_info["time_cost"], 35)
        self.assertEqual(dispatcher.submission.statistic_info["memory_cost"], 2048)

    def test_acm_does_not_compute_score(self):
        submission = self._submit()
        dispatcher = self._dispatcher(submission, JudgeStatus.ACCEPTED)
        dispatcher._compute_statistic_info([case(JudgeStatus.ACCEPTED)])
        self.assertNotIn("score", dispatcher.submission.statistic_info)

    def test_oi_sums_the_score_of_passed_cases(self):
        self.problem = self._create_problem(_id="D-2", rule_type=ProblemRuleType.OI)
        submission = self._submit()
        dispatcher = self._dispatcher(submission, JudgeStatus.PARTIALLY_ACCEPTED)
        resp = [case(JudgeStatus.ACCEPTED), case(JudgeStatus.WRONG_ANSWER)]
        dispatcher._compute_statistic_info(resp)
        # 1번(40점)만 맞았다
        self.assertEqual(dispatcher.submission.statistic_info["score"], 40)
        self.assertEqual(resp[0]["score"], 40)
        self.assertEqual(resp[1]["score"], 0)

    def test_oi_score_is_zero_when_test_case_score_is_short(self):
        # 테스트케이스 개수와 점수 정보가 어긋난 문제. 저장할 때 막고 있지만
        # 이미 어긋난 데이터가 있어도 채점이 예외로 죽지는 않아야 한다
        self.problem = self._create_problem(_id="D-3", rule_type=ProblemRuleType.OI,
                                            test_case_score=[{"output_name": "1.out",
                                                              "input_name": "1.in",
                                                              "score": 40}])
        submission = self._submit()
        dispatcher = self._dispatcher(submission, JudgeStatus.ACCEPTED)
        dispatcher._compute_statistic_info([case(JudgeStatus.ACCEPTED), case(JudgeStatus.ACCEPTED)])
        self.assertEqual(dispatcher.submission.statistic_info["score"], 0)


class AcmProblemStatusTest(DispatcherTestBase):
    def test_accepted_updates_problem_and_profile(self):
        submission = self._submit()
        self._dispatcher(submission, JudgeStatus.ACCEPTED).update_problem_status()

        problem = Problem.objects.get(id=self.problem.id)
        self.assertEqual(problem.submission_number, 1)
        self.assertEqual(problem.accepted_number, 1)
        self.assertEqual(problem.statistic_info[str(JudgeStatus.ACCEPTED)], 1)

        profile = self._profile()
        self.assertEqual(profile.submission_number, 1)
        self.assertEqual(profile.accepted_number, 1)
        solved = profile.acm_problems_status["problems"][str(self.problem.id)]
        self.assertEqual(solved["status"], JudgeStatus.ACCEPTED)
        self.assertEqual(solved["_id"], self.problem._id)

    def test_wrong_answer_counts_submission_only(self):
        submission = self._submit()
        self._dispatcher(submission, JudgeStatus.WRONG_ANSWER).update_problem_status()

        problem = Problem.objects.get(id=self.problem.id)
        self.assertEqual(problem.submission_number, 1)
        self.assertEqual(problem.accepted_number, 0)
        self.assertEqual(problem.statistic_info[str(JudgeStatus.WRONG_ANSWER)], 1)

        profile = self._profile()
        self.assertEqual(profile.submission_number, 1)
        self.assertEqual(profile.accepted_number, 0)

    def test_solving_after_a_wrong_answer_counts_once(self):
        first = self._submit()
        self._dispatcher(first, JudgeStatus.WRONG_ANSWER).update_problem_status()
        second = self._submit()
        self._dispatcher(second, JudgeStatus.ACCEPTED).update_problem_status()

        profile = self._profile()
        self.assertEqual(profile.submission_number, 2)
        self.assertEqual(profile.accepted_number, 1)
        self.assertEqual(profile.acm_problems_status["problems"][str(self.problem.id)]["status"],
                         JudgeStatus.ACCEPTED)

    def test_solving_the_same_problem_twice_does_not_count_twice(self):
        # 이미 푼 문제를 다시 맞혀도 "푼 문제 수"는 늘지 않아야 한다.
        # (문제 쪽 정답 수는 제출 단위라 늘어난다)
        for _ in range(2):
            submission = self._submit()
            self._dispatcher(submission, JudgeStatus.ACCEPTED).update_problem_status()

        profile = self._profile()
        self.assertEqual(profile.accepted_number, 1)
        self.assertEqual(profile.submission_number, 2)
        self.assertEqual(Problem.objects.get(id=self.problem.id).accepted_number, 2)


class OiProblemStatusTest(DispatcherTestBase):
    def setUp(self):
        super().setUp()
        self.problem = self._create_problem(_id="D-OI", rule_type=ProblemRuleType.OI)

    def test_score_is_added_to_total(self):
        submission = self._submit(statistic_info={"score": 40})
        self._dispatcher(submission, JudgeStatus.PARTIALLY_ACCEPTED).update_problem_status()

        profile = self._profile()
        self.assertEqual(profile.total_score, 40)
        status = profile.oi_problems_status["problems"][str(self.problem.id)]
        self.assertEqual(status["score"], 40)

    def test_higher_score_replaces_the_previous_one(self):
        # 40점을 받은 뒤 100점을 받으면 총점은 140 이 아니라 100 이어야 한다
        first = self._submit(statistic_info={"score": 40})
        self._dispatcher(first, JudgeStatus.PARTIALLY_ACCEPTED).update_problem_status()
        second = self._submit(statistic_info={"score": 100})
        self._dispatcher(second, JudgeStatus.ACCEPTED).update_problem_status()

        profile = self._profile()
        self.assertEqual(profile.total_score, 100)
        self.assertEqual(profile.accepted_number, 1)

    def test_score_does_not_change_after_the_problem_is_solved(self):
        first = self._submit(statistic_info={"score": 100})
        self._dispatcher(first, JudgeStatus.ACCEPTED).update_problem_status()
        second = self._submit(statistic_info={"score": 40})
        self._dispatcher(second, JudgeStatus.PARTIALLY_ACCEPTED).update_problem_status()

        profile = self._profile()
        self.assertEqual(profile.total_score, 100)


class RejudgeTest(DispatcherTestBase):
    def test_rejudge_moves_the_count_from_the_old_result_to_the_new_one(self):
        # 처음 채점: 오답
        submission = self._submit()
        self._dispatcher(submission, JudgeStatus.WRONG_ANSWER).update_problem_status()

        # 재채점: 정답으로 바뀜
        submission.refresh_from_db()
        self._rejudge_dispatcher(submission, JudgeStatus.ACCEPTED).update_problem_status_rejudge()

        problem = Problem.objects.get(id=self.problem.id)
        self.assertEqual(problem.accepted_number, 1)
        # 제출 수는 재채점으로 늘지 않는다
        self.assertEqual(problem.submission_number, 1)
        self.assertEqual(problem.statistic_info[str(JudgeStatus.ACCEPTED)], 1)
        self.assertEqual(problem.statistic_info[str(JudgeStatus.WRONG_ANSWER)], 0)

        profile = self._profile()
        self.assertEqual(profile.accepted_number, 1)
        self.assertEqual(profile.acm_problems_status["problems"][str(self.problem.id)]["status"],
                         JudgeStatus.ACCEPTED)

    def test_rejudge_keeps_the_solved_state_when_it_stays_accepted(self):
        submission = self._submit()
        self._dispatcher(submission, JudgeStatus.ACCEPTED).update_problem_status()

        submission.refresh_from_db()
        self._rejudge_dispatcher(submission, JudgeStatus.ACCEPTED).update_problem_status_rejudge()

        profile = self._profile()
        # 이미 푼 문제라 다시 세지 않는다
        self.assertEqual(profile.accepted_number, 1)

    def test_rejudge_decrements_the_old_result_by_one(self):
        # 예전에는 이전 결과의 키를 int 로 찾아서 항상 빗나갔고, 그 바람에
        # 오답이 몇 번이든 재채점 한 번에 0 이 되었다.
        for _ in range(3):
            self._dispatcher(self._submit(), JudgeStatus.WRONG_ANSWER).update_problem_status()
        self.assertEqual(Problem.objects.get(id=self.problem.id)
                         .statistic_info[str(JudgeStatus.WRONG_ANSWER)], 3)

        last = Submission.objects.filter(result=JudgeStatus.WRONG_ANSWER).first()
        self._rejudge_dispatcher(last, JudgeStatus.ACCEPTED).update_problem_status_rejudge()

        info = Problem.objects.get(id=self.problem.id).statistic_info
        self.assertEqual(info[str(JudgeStatus.WRONG_ANSWER)], 2)
        self.assertEqual(info[str(JudgeStatus.ACCEPTED)], 1)
