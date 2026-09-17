"""문제 화면의 실행. 제출하기 전에 자기 입력으로 코드를 돌려 보는 기능.

채점 서버는 부르지 않는다. API 는 무엇을 워커에 넘기는지를, 실행기는 채점 서버가
이렇게 답했을 때 화면에 무엇을 돌려주는지를 본다.
"""
from unittest import mock

from judge.run import MAX_OUTPUT_BYTES, CodeRunner, read_run, run_code, start_run
from problem.models import Problem, ProblemVisibility
from problem.utils import build_problem_template
from utils.api.tests import APITestCase

from .models import JudgeStatus, Submission

IO_MODE = {"io_mode": "Standard IO", "input": "input.txt", "output": "output.txt"}


def make_problem(created_by, **overrides):
    data = dict(title="두 수의 합", description="d", input_description="i", output_description="o",
                samples=[{"input": "1 2", "output": "3"}], test_case_id="x", test_case_score=[],
                time_limit=1000, memory_limit=256, languages=["C", "Python3"], template={},
                created_by=created_by, rule_type="ACM", io_mode=IO_MODE, difficulty="L1",
                visibility=ProblemVisibility.public, visible=True)
    data.update(overrides)
    return Problem.objects.create(**data)


class RunCodeAPITest(APITestCase):
    def setUp(self):
        self.admin = self.create_admin(login=False)
        self.problem = make_problem(self.admin)
        self.student = self.create_user("student", "test123")
        self.url = self.reverse("run_code_api")

        # 빈도 제한은 Redis 를 쓴다. 따로 보는 테스트 말고는 통과시킨다.
        throttle = mock.patch("utils.throttling.TokenBucket.consume", return_value=(True, 0))
        self.consume = throttle.start()
        self.addCleanup(throttle.stop)

        self.sent = []
        send = mock.patch("submission.views.oj.run_code_task.send",
                          side_effect=lambda *args: self.sent.append(args))
        send.start()
        self.addCleanup(send.stop)

    def _run(self, **overrides):
        data = {"problem_id": self.problem.id, "language": "Python3",
                "code": "print(input())", "input": "1 2"}
        data.update(overrides)
        return self.client.post(self.url, data=data)

    def test_requires_login(self):
        self.client.logout()
        self.assertFailed(self._run())

    def test_hands_the_code_and_input_to_the_worker(self):
        resp = self._run()
        self.assertSuccess(resp)
        token, user_id, spec = self.sent[0]
        self.assertEqual(token, resp.data["data"]["token"])
        self.assertEqual(user_id, self.student.id)
        self.assertEqual(spec["code"], "print(input())")
        self.assertEqual(spec["input"], "1 2")
        self.assertEqual(spec["time_limit"], 1000)

    def test_does_not_create_a_submission(self):
        """통계·순위·"푼 문제" 어디에도 남지 않아야 한다."""
        self._run()
        self.assertEqual(Submission.objects.count(), 0)

    def test_code_is_wrapped_with_the_template_like_a_submission(self):
        """빠뜨리면 제출은 되는데 실행은 컴파일 에러가 난다."""
        Problem.objects.filter(id=self.problem.id).update(template={
            "C": build_problem_template("#include <stdio.h>", "", "int main(){ return f(); }")})
        self._run(language="C", code="int f(){ return 0; }")
        code = self.sent[0][2]["code"]
        self.assertTrue(code.startswith("#include <stdio.h>"))
        self.assertIn("int f(){ return 0; }", code)
        self.assertTrue(code.rstrip().endswith("int main(){ return f(); }"))

    def test_block_coding_runs_as_python3(self):
        """블록에서 만든 파이썬 코드가 온다. 제출도 Python3 로 채점한다."""
        self.assertSuccess(self._run(language="Block Coding"))
        self.assertEqual(self.sent[0][2]["language"], "Python3")

    def test_language_must_be_allowed(self):
        Problem.objects.filter(id=self.problem.id).update(languages=["C"])
        self.assertFailed(self._run(), "Python3 언어는 이 문제에서 사용할 수 없습니다")

    def test_private_problem_is_hidden(self):
        """학급 문제는 제출과 똑같이 만든 교사와 배포받은 학급만 돌릴 수 있다."""
        Problem.objects.filter(id=self.problem.id).update(visibility=ProblemVisibility.private)
        self.assertFailed(self._run(), "문제가 존재하지 않습니다")
        self.assertEqual(self.sent, [])

    def test_empty_input_is_fine(self):
        """입력이 없는 문제도 있다."""
        self.assertSuccess(self._run(input=""))
        self.assertEqual(self.sent[0][2]["input"], "")

    def test_throttled(self):
        self.consume.return_value = (False, 3.2)
        resp = self._run()
        self.assertFailed(resp)
        self.assertIn("실행이 너무 잦습니다", resp.data["data"])
        self.assertEqual(self.sent, [])

    def test_throttle_is_separate_from_submissions(self):
        """같은 통이면 디버깅하다 제출을 못 하게 된다."""
        with mock.patch("submission.views.oj.TokenBucket") as bucket:
            bucket.return_value.consume.return_value = (True, 0)
            self._run()
        self.assertEqual(bucket.call_args.kwargs["key"], f"run:{self.student.id}")

    def test_only_the_owner_reads_the_result(self):
        """표만 알면 남의 코드 출력을 읽을 수 있으면 안 된다."""
        token = self._run().data["data"]["token"]
        run_code_task_result = {"result": "ok", "output": "3\n"}
        with mock.patch("judge.run.CodeRunner.run", return_value=run_code_task_result):
            run_code(token, self.student.id, self.sent[0][2])

        resp = self.client.get(self.url + f"?token={token}")
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["output"], "3\n")
        self.assertNotIn("user_id", resp.data["data"])

        self.client.logout()
        self.create_user("other", "test123")
        self.assertFailed(self.client.get(self.url + f"?token={token}"))


def judged(result=JudgeStatus.ACCEPTED, output="3\n", **extra):
    """채점 서버의 /judge 응답 모양(케이스 하나)"""
    case = {"test_case": "1", "result": result, "output": output,
            "cpu_time": 12, "memory": 3 * 1024 * 1024}
    case.update(extra)
    return {"err": None, "data": [case]}


class CodeRunnerTest(APITestCase):
    SPEC = {"language": "Python3", "code": "print(input())", "input": "1 2",
            "time_limit": 1000, "memory_limit": 256, "io_mode": IO_MODE}

    def _run(self, response, server=True, spec=None):
        with mock.patch.object(CodeRunner, "_request", return_value=response) as request, \
                mock.patch("judge.run.ChooseJudgeServer") as choose:
            choose.return_value.__enter__.return_value = (
                mock.Mock(service_url="http://s") if server else None)
            result = CodeRunner(spec or self.SPEC).run()
        return result, request

    def test_output_comes_back(self):
        result, request = self._run(judged())
        self.assertEqual(result["result"], "ok")
        self.assertEqual(result["output"], "3\n")
        self.assertFalse(result["truncated"])
        self.assertEqual(result["time"], 12)
        # 정답을 모르므로 빈 출력을 주고, 출력을 돌려받는다
        sent = request.call_args.kwargs["data"]
        self.assertEqual(sent["test_case"], [{"input": "1 2", "output": ""}])
        self.assertTrue(sent["output"])

    def test_wrong_answer_just_means_it_finished(self):
        """정답을 주지 않았으니 판정이 오답인 것은 아무 뜻이 없다."""
        result, _ = self._run(judged(result=JudgeStatus.WRONG_ANSWER))
        self.assertEqual(result["result"], "ok")

    def test_long_output_is_cut(self):
        """반복문에서 print 를 멈추지 않으면 16MB 가 브라우저로 간다."""
        result, _ = self._run(judged(output="a" * (MAX_OUTPUT_BYTES + 100)))
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["output"]), MAX_OUTPUT_BYTES)

    def test_cutting_does_not_break_korean(self):
        """바이트로 자르면 한글 한 글자가 반으로 갈릴 수 있다."""
        result, _ = self._run(judged(output="가" * MAX_OUTPUT_BYTES))
        self.assertTrue(result["truncated"])
        self.assertEqual(set(result["output"]), {"가"})

    def test_compile_error(self):
        result, _ = self._run({"err": "CompileError", "data": "SyntaxError: invalid syntax"})
        self.assertEqual(result["result"], "compile_error")
        self.assertIn("SyntaxError", result["message"])

    def test_runtime_error_keeps_the_traceback(self):
        """채점 서버가 stderr 를 출력에 함께 쓴다. 디버깅에 제일 필요한 것이다."""
        result, _ = self._run(judged(result=JudgeStatus.RUNTIME_ERROR,
                                     output="Traceback ...\nValueError: bad"))
        self.assertEqual(result["result"], "runtime_error")
        self.assertIn("ValueError", result["output"])

    def test_time_limit(self):
        result, _ = self._run(judged(result=JudgeStatus.REAL_TIME_LIMIT_EXCEEDED, output=""))
        self.assertEqual(result["result"], "time_limit")

    def test_busy_judge_server_does_not_wait(self):
        """실행이 제출을 밀어내면 안 된다. 자리가 없으면 바로 돌려준다."""
        result, request = self._run(judged(), server=False)
        self.assertEqual(result["result"], "busy")
        request.assert_not_called()

    def test_unknown_language(self):
        result, request = self._run(judged(), spec=dict(self.SPEC, language="없는언어"))
        self.assertEqual(result["result"], "system_error")
        request.assert_not_called()

    def test_result_record_belongs_to_one_user(self):
        token = start_run(user_id=1)
        with mock.patch.object(CodeRunner, "run", return_value={"result": "ok", "output": ""}):
            run_code(token, 1, self.SPEC)
        self.assertEqual(read_run(token, 1)["status"], "done")
        self.assertIsNone(read_run(token, 2))
