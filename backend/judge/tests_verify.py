"""정답 코드로 테스트케이스가 맞는지 확인하는 부분.

채점 서버를 부르지 않고, 서버가 이렇게 답한다고 정해놓고 검증한다.
보는 것은 "그 답을 사람이 알아볼 수 있는 결과로 바꾸는가" 다.
"""
import os
from unittest import mock

from django.conf import settings
from django.utils.timezone import now

from problem.models import Problem
from submission.models import JudgeStatus
from utils.api.tests import APITestCase

from .tests import DEFAULT_PROBLEM_DATA
from .verify import (SolutionVerifier, attach_verification, clear_verification,
                     fingerprint, run_verification, spec_of, start_verification)


def judged(*results):
    """채점 서버의 /judge 응답 모양"""
    return {"err": None, "data": [{"test_case": str(i), "result": r}
                                  for i, r in enumerate(results, start=1)]}


class VerifyTestBase(APITestCase):
    def setUp(self):
        self.admin = self.create_admin("teacher", "test123", login=False)
        data = dict(DEFAULT_PROBLEM_DATA)
        data["created_by"] = self.admin
        self.problem = Problem.objects.create(
            **data, solver_language="C", solver_code="int main(){}")

    def _run(self, response, spec=None):
        """채점 서버가 이렇게 답했을 때의 결과"""
        spec = spec or spec_of(self.problem)
        token = start_verification(spec)
        with mock.patch.object(SolutionVerifier, "_request", return_value=response), \
                mock.patch("judge.verify.ChooseJudgeServer") as choose:
            choose.return_value.__enter__.return_value = mock.Mock(service_url="http://s")
            passed, message = run_verification(token, spec, sleep=lambda _: None)
        self.token = token
        return passed, message


class SolutionVerifyTest(VerifyTestBase):
    def test_all_cases_pass(self):
        passed, message = self._run(judged(JudgeStatus.ACCEPTED, JudgeStatus.ACCEPTED))
        self.assertTrue(passed)
        self.assertIn("2개를 모두 통과", message)

    def test_result_reaches_the_problem_only_through_save(self):
        """저장 전에도 검증하므로 결과는 문제가 아니라 표에 담긴다."""
        self._run(judged(JudgeStatus.ACCEPTED))
        self.assertFalse(Problem.objects.get(id=self.problem.id).solver_passed)

        attach_verification(self.problem, self.token, spec_of(self.problem))

        problem = Problem.objects.get(id=self.problem.id)
        self.assertTrue(problem.solver_passed)
        self.assertIsNotNone(problem.solver_verified_at)

    def test_points_at_the_first_failing_case(self):
        """어느 케이스가 문제인지 알아야 고칠 수 있다"""
        passed, message = self._run(judged(JudgeStatus.ACCEPTED,
                                           JudgeStatus.WRONG_ANSWER,
                                           JudgeStatus.WRONG_ANSWER))
        self.assertFalse(passed)
        self.assertIn("2번 케이스", message)
        self.assertIn("넣어 둔 출력과 다릅니다", message)
        self.assertIn("2개", message)

    def test_case_numbers_are_compared_as_numbers(self):
        """10 번만 틀렸는데 문자열로 고르면 10 이 2 보다 앞선다"""
        results = [JudgeStatus.ACCEPTED] * 12
        results[1] = JudgeStatus.WRONG_ANSWER
        results[9] = JudgeStatus.WRONG_ANSWER
        _, message = self._run(judged(*results))
        self.assertIn("2번 케이스", message)

    def test_time_limit_is_reported_as_such(self):
        """제한이 빡빡하면 학생도 똑같이 겪는다. 오답과 구분해서 알려준다."""
        _, message = self._run(judged(JudgeStatus.CPU_TIME_LIMIT_EXCEEDED))
        self.assertIn("시간이 초과", message)

    def test_compile_error_is_not_a_case_failure(self):
        """아무것도 확인되지 않았다. 케이스가 틀렸다고 말하면 안 된다."""
        passed, message = self._run({"err": "CompileError", "data": "expected ';'"})
        self.assertFalse(passed)
        self.assertIn("컴파일되지 않습니다", message)
        self.assertIn("expected ';'", message)

    def test_unknown_language_does_not_call_the_judge_server(self):
        spec = dict(spec_of(self.problem), solver_language="없는언어")
        with mock.patch.object(SolutionVerifier, "_request") as request:
            passed, message = run_verification(start_verification(spec), spec,
                                               sleep=lambda _: None)
        request.assert_not_called()
        self.assertFalse(passed)
        self.assertIn("설정이 없습니다", message)

    def test_busy_judge_servers_are_not_a_verification_failure(self):
        """서버 사정은 문제의 옳고 그름과 무관하다. 다시 눌러보라고 알린다."""
        spec = spec_of(self.problem)
        with mock.patch("judge.verify.ChooseJudgeServer") as choose:
            choose.return_value.__enter__.return_value = None
            passed, message = run_verification(start_verification(spec), spec,
                                               sleep=lambda _: None)
        self.assertFalse(passed)
        self.assertIn("다시 눌러주세요", message)

    def test_runs_on_the_materialized_case_set(self):
        """화면이 보낸 케이스는 뷰가 파일로 만들어 둔다.

        인라인으로 넘기면 {"keep": 번호} 처럼 내용이 없는 항목을 풀 수 없다.
        채점 서버에는 그 묶음의 id 를 준다.
        """
        spec = dict(spec_of(self.problem), test_case_id=None,
                    cases=[{"keep": 1}], resolved_test_case_id="tmp1234")
        with mock.patch.object(SolutionVerifier, "_request",
                               return_value=judged(JudgeStatus.ACCEPTED)) as request, \
                mock.patch("judge.verify.ChooseJudgeServer") as choose:
            choose.return_value.__enter__.return_value = mock.Mock(service_url="http://s")
            passed, _ = run_verification(start_verification(spec), spec, sleep=lambda _: None)
        self.assertTrue(passed)
        sent = request.call_args.kwargs["data"]
        self.assertEqual(sent["test_case_id"], "tmp1234")
        self.assertNotIn("test_case", sent)

    def test_temporary_case_set_is_removed(self):
        """검증만을 위해 만든 묶음이다. 두면 디스크에 쌓이기만 한다."""
        path = os.path.join(settings.TEST_CASE_DIR, "tmpverify")
        os.makedirs(path, exist_ok=True)
        spec = dict(spec_of(self.problem), test_case_id=None, cases=[{"keep": 1}],
                    resolved_test_case_id="tmpverify", resolved_is_temporary=True)
        with mock.patch.object(SolutionVerifier, "_request",
                               return_value=judged(JudgeStatus.ACCEPTED)), \
                mock.patch("judge.verify.ChooseJudgeServer") as choose:
            choose.return_value.__enter__.return_value = mock.Mock(service_url="http://s")
            run_verification(start_verification(spec), spec, sleep=lambda _: None)
        self.assertFalse(os.path.exists(path))

    def test_temporary_set_id_is_not_part_of_the_fingerprint(self):
        """묶음은 검증할 때마다 새로 만들어진다. id 가 지문에 들어가면 결과가 영영 안 붙는다."""
        spec = dict(spec_of(self.problem), cases=[{"keep": 1}])
        self.assertEqual(fingerprint(dict(spec, resolved_test_case_id="a")),
                         fingerprint(dict(spec, resolved_test_case_id="b")))


class VerificationFingerprintTest(VerifyTestBase):
    """검증한 내용과 저장하는 내용이 같을 때만 결과를 붙인다.

    "검증 → 케이스 수정 → 저장" 순서면, 저장되는 내용은 검증된 적이 없는데도
    "통과함" 이 붙는다. 새로고침 후에도 남고 심사 화면이 읽는 값이라 조용히
    거짓이 된다. 대조는 서버가 한다 - 화면이 말하게 하면 믿을 것이 못 된다.
    """
    def test_changing_the_cases_drops_the_result(self):
        spec = dict(spec_of(self.problem), test_case_id=None,
                    cases=[{"input": "1", "output": "1"}])
        self._run(judged(JudgeStatus.ACCEPTED), spec=spec)

        changed = dict(spec, cases=[{"input": "2", "output": "2"}])
        self.assertFalse(attach_verification(self.problem, self.token, changed))
        self.assertFalse(Problem.objects.get(id=self.problem.id).solver_passed)

    def test_changing_the_solver_drops_the_result(self):
        self._run(judged(JudgeStatus.ACCEPTED))
        changed = dict(spec_of(self.problem), solver_code="int main(){return 1;}")
        self.assertFalse(attach_verification(self.problem, self.token, changed))

    def test_changing_the_time_limit_drops_the_result(self):
        """제한을 줄이면 통과하던 것이 시간 초과가 될 수 있다."""
        self._run(judged(JudgeStatus.ACCEPTED))
        changed = dict(spec_of(self.problem), time_limit=1)
        self.assertFalse(attach_verification(self.problem, self.token, changed))

    def test_unrelated_changes_keep_the_result(self):
        """제목처럼 판정과 무관한 것을 고쳤다고 다시 검증시키면 못 쓴다."""
        self._run(judged(JudgeStatus.ACCEPTED))
        self.assertTrue(attach_verification(self.problem, self.token, spec_of(self.problem)))

    def test_unknown_token_is_ignored(self):
        self.assertFalse(attach_verification(self.problem, "없는표", spec_of(self.problem)))

    def test_result_still_running_is_not_attached(self):
        spec = spec_of(self.problem)
        token = start_verification(spec)
        self.assertFalse(attach_verification(self.problem, token, spec))

    def test_fingerprint_ignores_key_order(self):
        spec = spec_of(self.problem)
        self.assertEqual(fingerprint(spec), fingerprint(dict(reversed(list(spec.items())))))


class ClearVerificationTest(VerifyTestBase):
    def test_result_is_cleared_but_the_code_stays(self):
        """테스트케이스가 바뀌면 지난 결과는 거짓말이 된다.

        정답 코드는 남겨서 검증 버튼만 다시 누르면 되게 한다.
        """
        Problem.objects.filter(id=self.problem.id).update(
            solver_passed=True, solver_message="통과", solver_verified_at=now())

        clear_verification(self.problem.id)

        problem = Problem.objects.get(id=self.problem.id)
        self.assertFalse(problem.solver_passed)
        self.assertEqual(problem.solver_message, "")
        self.assertIsNone(problem.solver_verified_at)
        self.assertEqual(problem.solver_code, "int main(){}")
