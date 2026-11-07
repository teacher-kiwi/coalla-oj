"""바로 과제 1단계: 데이터와 학생 출입증.

학생은 로그인하지 않고 과제마다 받는 출입증(쿠키)으로 알아본다. 들어오는 순간
보이지 않는 임시 계정이 생기고, 그 계정은 로그인·순위·목록 어디에도 나오면 안 된다.
"""
from datetime import timedelta
from unittest import mock

from django.utils.timezone import now

from account.models import AdminType, User
from contest.models import ContestRuleType
from problem.models import Problem, ProblemVisibility
from submission.models import Submission
from utils.api.tests import APITestCase
from utils.cache import cache

from . import session
from .models import Homework, HomeworkParticipant, HomeworkProblem


def make_problem(user, title="두 수의 합"):
    return Problem.objects.create(
        title=title, description="d", input_description="i", output_description="o",
        samples=[], test_case_id="x", test_case_score=[], time_limit=1000, memory_limit=256,
        languages=["Python3"], template={}, created_by=user, rule_type="ACM", io_mode={},
        difficulty="L1", visibility=ProblemVisibility.private)


class HomeworkTestBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.teacher = self.create_teacher(username="김선생", login=False)
        self.problem = make_problem(self.teacher)
        self.homework = self.make_homework()

    def make_homework(self, **overrides):
        data = {"code": Homework.generate_code(), "title": "1차시 반복문",
                "created_by": self.teacher, "languages": ["Python3"],
                "end_time": now() + timedelta(hours=1)}
        data.update(overrides)
        homework = Homework.objects.create(**data)
        HomeworkProblem.objects.create(homework=homework, problem=self.problem)
        return homework

    def join(self, number="5", nickname="코알라", pin="1234", homework=None):
        homework = homework or self.homework
        return self.client.post(self.reverse("homework_join_api", kwargs={"code": homework.code}),
                                data={"number": number, "nickname": nickname, "pin": pin})

    def me(self, homework=None):
        homework = homework or self.homework
        return self.client.get(self.reverse("homework_me_api", kwargs={"code": homework.code}))


class JoinTest(HomeworkTestBase):
    def test_first_join_makes_a_hidden_guest_account(self):
        resp = self.join()
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["participant"]["number"], 5)
        self.assertEqual([p["id"] for p in resp.data["data"]["homework"]["problems"]],
                         [self.problem.id])

        user = HomeworkParticipant.objects.get().user
        self.assertEqual(user.admin_type, AdminType.GUEST)
        self.assertFalse(user.has_usable_password())
        # 채점이 푼 문제 현황을 여기에 적는다. 없으면 채점이 끝나고 죽는다.
        self.assertTrue(hasattr(user, "userprofile"))

    def test_pass_is_scoped_to_this_homework(self):
        cookie = self.join().cookies[session.COOKIE_NAME]
        self.assertEqual(cookie["path"], f"/api/hw/{self.homework.code}")
        self.assertTrue(cookie["httponly"])

    def test_number_ignores_leading_zeros(self):
        self.assertSuccess(self.join(number="05"))
        # 다시 들어올 때는 닉네임을 넣지 않아도 된다
        self.assertSuccess(self.join(number="5", nickname=""))
        resp = self.join(number="5", nickname="다른이름")
        self.assertSuccess(resp)
        # 다시 들어올 때 닉네임은 바꾸지 않는다. 바꾸는 것은 교사의 일이다.
        self.assertEqual(resp.data["data"]["participant"]["nickname"], "코알라")
        self.assertEqual(HomeworkParticipant.objects.count(), 1)

    def test_invalid_inputs(self):
        for number, pin in (("123456", "1234"), ("abc", "1234"), ("", "1234"),
                            ("5", "123"), ("5", "12345"), ("5", "abcd")):
            self.assertFailed(self.join(number=number, pin=pin))
        self.assertFailed(self.join(nickname="   "), "닉네임을 넣어주세요")
        self.assertFailed(self.join(nickname="가" * 21))
        self.assertFalse(HomeworkParticipant.objects.exists())

    def test_wrong_pin_cannot_take_the_seat(self):
        self.join()
        self.client.cookies.clear()
        self.assertFailed(self.join(pin="9999"), "이미 들어온 번호입니다. 4자리 숫자가 맞지 않습니다")
        self.assertFailed(self.me())

    def test_wrong_pin_locks_only_that_seat(self):
        self.join(number="5")
        self.join(number="6", pin="5555")
        self.client.cookies.clear()
        for _ in range(5):
            self.join(number="5", pin="9999")
        # 맞는 숫자여도 잠긴 동안은 안 된다
        resp = self.join(number="5", pin="1234")
        self.assertFailed(resp)
        self.assertIn("너무 많이 틀렸습니다", resp.data["data"])
        # 옆자리 학생은 영향을 받지 않는다(같은 교실 = 같은 IP)
        self.assertSuccess(self.join(number="6", pin="5555"))

    def test_ended_homework(self):
        self.join(number="5")
        self.homework.ended_at = now()
        self.homework.save()
        self.client.cookies.clear()
        self.assertFailed(self.join(number="7"), "종료된 과제라 새로 들어갈 수 없습니다")
        # 이미 들어온 학생은 자기 결과를 보러 다시 들어올 수 있다
        resp = self.join(number="5")
        self.assertSuccess(resp)
        self.assertTrue(resp.data["data"]["homework"]["ended"])

    def test_deadline_ends_it_without_pressing_end(self):
        self.homework.end_time = now() - timedelta(minutes=1)
        self.homework.save()
        self.assertFailed(self.join(), "종료된 과제라 새로 들어갈 수 없습니다")

    def test_entry_lock(self):
        self.join(number="5")
        self.homework.entry_locked = True
        self.homework.save()
        self.client.cookies.clear()
        self.assertFailed(self.join(number="7"), "선생님이 새 입장을 막아 두었습니다")
        self.assertSuccess(self.join(number="5"))


class PassTest(HomeworkTestBase):
    def test_me_needs_a_pass(self):
        resp = self.me()
        self.assertFailed(resp)
        self.assertEqual(resp.data["error"], "hw-join-required")
        self.join()
        self.assertSuccess(self.me())

    def test_pass_from_another_homework_is_not_accepted(self):
        """테스트 클라이언트는 쿠키 경로를 무시하고 다 보낸다. 서버도 막아야 한다."""
        other = self.make_homework(title="다른 반 과제")
        self.join(homework=other)
        self.assertFailed(self.me())

    def test_forged_pass_is_rejected(self):
        self.join()
        self.client.cookies[session.COOKIE_NAME] = "1:forged"
        self.assertFailed(self.me())

    def test_leaving_this_device(self):
        self.join()
        self.client.delete(self.reverse("homework_me_api", kwargs={"code": self.homework.code}))
        self.assertFailed(self.me())
        self.assertTrue(HomeworkParticipant.objects.exists())

    def test_login_is_untouched(self):
        """교사로 로그인한 채 학생 화면을 시험해도 로그인은 그대로다."""
        self.client.login(username="김선생", password="teacher")
        self.assertSuccess(self.join())
        profile = self.client.get(self.reverse("user_profile_api")).data["data"]
        self.assertEqual(profile["user"]["username"], "김선생")

    def test_guest_cannot_log_in(self):
        self.join()
        username = HomeworkParticipant.objects.get().user.username
        resp = self.client.post(self.reverse("user_login_api"),
                                data={"username": username, "password": "1234"})
        self.assertFailed(resp)


class WrongCodeTest(HomeworkTestBase):
    def test_unknown_code(self):
        resp = self.client.get(self.reverse("homework_api", kwargs={"code": "000000"}))
        self.assertFailed(resp, "없는 과제 코드입니다. 선생님께 받은 6자리 숫자를 확인해주세요")

    @mock.patch("homework.views.oj.WRONG_CODE_LIMIT", 3)
    def test_guessing_codes_is_slowed(self):
        for _ in range(3):
            self.client.get(self.reverse("homework_api", kwargs={"code": "000000"}))
        resp = self.client.get(self.reverse("homework_api", kwargs={"code": self.homework.code}))
        self.assertFailed(resp, "코드를 너무 많이 틀렸습니다. 10분 뒤에 다시 시도해주세요")

    def test_right_codes_are_not_counted(self):
        for _ in range(5):
            self.assertSuccess(self.client.get(
                self.reverse("homework_api", kwargs={"code": self.homework.code})))


class RecordsTest(HomeworkTestBase):
    def _submit_as_guest(self):
        self.join()
        user = HomeworkParticipant.objects.get().user
        return Submission.objects.create(user=user, problem=self.problem, code="print(1)",
                                         language="Python3")

    def test_deleting_the_homework_deletes_guests_and_their_submissions(self):
        self._submit_as_guest()
        self.homework.delete()
        self.assertFalse(User.objects.filter(admin_type=AdminType.GUEST).exists())
        self.assertFalse(Submission.objects.exists())
        self.assertTrue(User.objects.filter(id=self.teacher.id).exists())

    def test_removing_a_participant_deletes_the_guest(self):
        self._submit_as_guest()
        HomeworkParticipant.objects.get().delete()
        self.assertFalse(User.objects.filter(admin_type=AdminType.GUEST).exists())
        self.assertFalse(Submission.objects.exists())

    def test_guests_are_not_in_public_lists(self):
        self._submit_as_guest()
        guest = User.objects.get(admin_type=AdminType.GUEST)
        guest.userprofile.accepted_number = 99
        guest.userprofile.save()

        rank = self.client.get(self.reverse("user_rank_api"), data={"rule": ContestRuleType.ACM})
        self.assertNotIn(guest.username,
                         [row["user"]["username"] for row in rank.data["data"]["results"]])
        submissions = self.client.get(self.reverse("submission_list_api"), data={"limit": 10})
        self.assertEqual(submissions.data["data"]["total"], 0)

        self.create_super_admin()
        users = self.client.get(self.reverse("user_admin_api"), data={"limit": 50})
        self.assertNotIn(guest.username, [u["username"] for u in users.data["data"]["results"]])


class ProblemDeleteTest(HomeworkTestBase):
    def test_problem_in_an_open_homework_cannot_be_deleted(self):
        self.client.login(username="김선생", password="teacher")
        url = self.reverse("teacher_problem_api") + f"?id={self.problem.id}"
        resp = self.client.delete(url)
        self.assertFailed(resp)
        self.assertIn("진행 중인 바로 과제", resp.data["data"])

        self.homework.ended_at = now()
        self.homework.save()
        self.assertSuccess(self.client.delete(url))


class StudentSolveTest(HomeworkTestBase):
    """2단계: 출입증으로 문제를 보고, 내고, 결과를 본다."""
    def setUp(self):
        super().setUp()
        self.problem.languages = ["C", "Python3"]
        self.problem.solver_language = "Python3"
        self.problem.solver_code = "print('정답')"
        self.problem.save()
        self.homework.languages = ["Python3", "Block Coding"]
        self.homework.save()
        patcher = mock.patch("homework.views.oj.judge_task.send")
        self.judge = patcher.start()
        self.addCleanup(patcher.stop)

    def url(self, name):
        return self.reverse(name, kwargs={"code": self.homework.code})

    def get_problem(self, problem=None):
        return self.client.get(self.url("homework_problem_api"),
                               data={"problem_id": (problem or self.problem).id})

    def submit(self, language="Python3", problem=None, code="print(1)"):
        return self.client.post(self.url("homework_submission_api"), data={
            "problem_id": (problem or self.problem).id, "language": language, "code": code})

    def test_everything_needs_a_pass(self):
        for resp in (self.get_problem(), self.submit(),
                     self.client.get(self.url("homework_submission_api"), data={"id": "x"})):
            self.assertEqual(resp.data["error"], "hw-join-required")

    def test_problem_shows_only_what_a_student_needs(self):
        self.join()
        resp = self.get_problem()
        self.assertSuccess(resp)
        data = resp.data["data"]
        self.assertEqual(data["title"], "두 수의 합")
        # 교사가 고른 것과 문제가 허용한 것의 겹침(C 는 과제에서 고르지 않았다)
        self.assertEqual(data["languages"], ["Python3", "Block Coding"])
        for hidden in ("solver_code", "solver_language", "test_case_id", "accepted_number",
                       "created_by"):
            self.assertNotIn(hidden, data)
        self.assertIsNone(data["last_submission"])

    def test_problems_outside_the_homework_are_not_shown(self):
        self.join()
        other = make_problem(self.teacher, title="과제에 없는 문제")
        self.assertFailed(self.get_problem(other), "이 과제에 없는 문제입니다")
        self.assertFailed(self.submit(problem=other), "이 과제에 없는 문제입니다")

    def test_submit_as_the_participant_even_when_logged_in(self):
        """교사로 로그인한 브라우저여도 제출은 과제 참가자의 것이다."""
        self.client.login(username="김선생", password="teacher")
        self.join()
        resp = self.submit(code="print(2)")
        self.assertSuccess(resp)
        submission = Submission.objects.get(id=resp.data["data"]["submission_id"])
        self.assertEqual(submission.user, HomeworkParticipant.objects.get().user)
        self.judge.assert_called_once_with(submission.id, self.problem.id)

        # 다시 열면 마지막으로 낸 코드를 이어서 쓴다
        last = self.get_problem().data["data"]["last_submission"]
        self.assertEqual(last["code"], "print(2)")

    def test_block_coding(self):
        self.join()
        self.assertSuccess(self.submit(language="Block Coding"))

    def test_language_must_be_allowed(self):
        self.join()
        self.assertFailed(self.submit(language="C"), "C 언어는 이 과제에서 쓸 수 없습니다")

    def test_cannot_submit_after_the_end(self):
        self.join()
        self.homework.ended_at = now()
        self.homework.save()
        self.assertFailed(self.submit(), "종료된 과제입니다. 결과만 볼 수 있습니다")
        # 결과는 계속 볼 수 있다
        self.assertSuccess(self.get_problem())

    def test_status_per_problem(self):
        self.join()
        self.submit()
        Submission.objects.update(result=0)
        self.submit()
        problems = self.me().data["data"]["homework"]["problems"]
        self.assertEqual(problems[0]["attempts"], 2)
        self.assertTrue(problems[0]["solved"])

    def test_only_my_submissions(self):
        self.join(number="1")
        theirs = self.submit().data["data"]["submission_id"]
        self.client.cookies.clear()
        self.join(number="2")
        resp = self.client.get(self.url("homework_submission_api"), data={"id": theirs})
        self.assertFailed(resp, "제출 기록이 존재하지 않습니다")
        mine = self.client.get(self.url("homework_submission_api"),
                               data={"problem_id": self.problem.id})
        self.assertEqual(mine.data["data"], [])

    @mock.patch("homework.views.oj.run_code_task.send")
    def test_run(self, run):
        self.join()
        resp = self.client.post(self.url("homework_run_api"), data={
            "problem_id": self.problem.id, "language": "Python3", "code": "print(input())",
            "input": "5"})
        self.assertSuccess(resp)
        token, user_id, spec = run.call_args.args
        self.assertEqual(user_id, HomeworkParticipant.objects.get().user_id)
        self.assertEqual(spec["input"], "5")
        result = self.client.get(self.url("homework_run_api"), data={"token": token})
        self.assertSuccess(result)
        self.assertEqual(result.data["data"]["status"], "running")
