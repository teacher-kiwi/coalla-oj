"""바로 과제 1단계: 데이터와 학생 출입증.

학생은 로그인하지 않고 과제마다 받는 출입증(쿠키)으로 알아본다. 들어오는 순간
보이지 않는 임시 계정이 생기고, 그 계정은 로그인·순위·목록 어디에도 나오면 안 된다.
"""
import io
import zipfile
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


class FreshBrowserTest(HomeworkTestBase):
    """링크·QR 로 과제 화면에 바로 들어온 브라우저. 사이트의 다른 화면을 거치지 않았다.

    과제 화면은 상단 메뉴를 감춘다. 사이트 화면에서는 그 메뉴가 /api/profile 을 불러
    CSRF 쿠키를 받는데, 과제 화면만 열면 쿠키가 없어 입장(POST)이 403 으로 막혔다.
    """
    def setUp(self):
        super().setUp()
        self.client = self.client_class(enforce_csrf_checks=True)

    def test_can_join_after_opening_the_homework_page(self):
        for name in ("homework_me_api", "homework_api"):
            self.client = self.client_class(enforce_csrf_checks=True)
            self.client.get(self.reverse(name, kwargs={"code": self.homework.code}))
            token = self.client.cookies["csrftoken"].value
            resp = self.client.post(
                self.reverse("homework_join_api", kwargs={"code": self.homework.code}),
                data={"number": "5", "nickname": "코알라", "pin": "1234"},
                HTTP_X_CSRFTOKEN=token)
            self.assertSuccess(resp)

    def test_without_the_token_it_is_refused(self):
        resp = self.join()
        self.assertEqual(resp.status_code, 403)


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


class TeacherHomeworkTest(HomeworkTestBase):
    """3단계: 교사가 만들고, 현황판을 보고, 진행을 바꾼다."""
    def setUp(self):
        super().setUp()
        self.client.login(username="김선생", password="teacher")
        self.url = self.reverse("teacher_homework_api")
        self.second = make_problem(self.teacher, title="반복문")

    def create(self, **overrides):
        data = {"title": " 3월 7일 반복문 ", "problems": [self.second.id, self.problem.id],
                "languages": ["Python3", "Block Coding"],
                "end_time": (now() + timedelta(hours=1)).isoformat()}
        data.update(overrides)
        return self.client.post(self.url, data=data)

    def test_create(self):
        resp = self.create()
        self.assertSuccess(resp)
        data = resp.data["data"]
        self.assertRegex(data["code"], r"^\d{6}$")
        self.assertEqual(data["title"], "3월 7일 반복문")
        # 고른 순서 그대로
        self.assertEqual([p["id"] for p in data["problems"]], [self.second.id, self.problem.id])
        self.assertFalse(data["ended"])

    def test_create_rules(self):
        self.assertFailed(self.create(end_time=(now() - timedelta(minutes=1)).isoformat()),
                          "마감 시각은 지금보다 뒤여야 합니다")
        self.assertFailed(self.create(languages=["Fortran"]))
        self.assertFailed(self.create(problems=[]))
        # 다른 교사의 비공개 문제는 담을 수 없다
        other = make_problem(self.create_teacher(username="박선생", login=False), title="남의 문제")
        self.assertFailed(self.create(problems=[other.id]))

    def test_regular_user_cannot_create(self):
        self.client.logout()
        self.create_user("학생", "pass")
        self.assertFailed(self.create())

    def test_teachers_see_only_their_own(self):
        self.create()
        self.client.logout()
        self.create_teacher(username="박선생")
        listed = self.client.get(self.url).data["data"]
        self.assertEqual(listed, [])
        self.assertFailed(self.client.get(self.url, data={"id": self.homework.id}))

    def test_report_lists_newest_first(self):
        newer = self.create().data["data"]
        listed = self.client.get(self.url).data["data"]
        self.assertEqual([h["id"] for h in listed], [newer["id"], self.homework.id])

    def test_end_early_then_cannot_reopen(self):
        resp = self.client.put(self.url, data={"id": self.homework.id, "end": True})
        self.assertSuccess(resp)
        self.assertTrue(resp.data["data"]["ended"])
        self.assertFailed(self.client.put(self.url, data={
            "id": self.homework.id, "end_time": (now() + timedelta(hours=2)).isoformat()}),
            "이미 종료된 과제입니다")
        # 제목은 끝난 뒤에도 고칠 수 있다(레포트에서 알아보기 쉽게)
        self.assertSuccess(self.client.put(self.url, data={"id": self.homework.id, "title": "새 제목"}))

    def test_extend_and_lock(self):
        later = now() + timedelta(hours=5)
        self.assertSuccess(self.client.put(self.url, data={
            "id": self.homework.id, "end_time": later.isoformat(), "entry_locked": True}))
        self.homework.refresh_from_db()
        self.assertEqual(self.homework.end_time, later)
        self.assertTrue(self.homework.entry_locked)

    def _guest_submits(self, number, result):
        self.client_as_student = self.client_class()
        self.client_as_student.post(
            self.reverse("homework_join_api", kwargs={"code": self.homework.code}),
            data={"number": number, "nickname": f"학생{number}", "pin": "1234"})
        user = HomeworkParticipant.objects.get(number=int(number)).user
        return Submission.objects.create(user=user, problem=self.problem, code="print(1)",
                                         language="Python3", result=result)

    def test_board(self):
        self._guest_submits("3", -1)
        self._guest_submits("3", 0)
        self._guest_submits("1", -1)
        resp = self.client.get(self.reverse("teacher_homework_board_api"),
                               data={"id": self.homework.id})
        self.assertSuccess(resp)
        data = resp.data["data"]
        rows = data["participants"]
        self.assertEqual([r["number"] for r in rows], [1, 3])
        self.assertEqual(rows[1]["pin"], "1234")
        self.assertEqual(rows[1]["cells"][str(self.problem.id)],
                         {"attempts": 2, "solved": True, "last_result": 0})
        self.assertEqual(rows[0]["cells"][str(self.problem.id)]["solved"], False)
        self.assertEqual(data["homework"]["problems"][0]["solved_count"], 1)

    def test_cell_submissions_include_code(self):
        self._guest_submits("3", 0)
        participant = HomeworkParticipant.objects.get()
        resp = self.client.get(self.reverse("teacher_homework_submission_api"),
                               data={"participant_id": participant.id, "problem_id": self.problem.id})
        self.assertEqual(resp.data["data"][0]["code"], "print(1)")

    def test_manage_participants(self):
        self._guest_submits("3", 0)
        participant = HomeworkParticipant.objects.get()
        url = self.reverse("teacher_homework_participant_api")
        # 4자리 숫자를 틀려 잠긴 자리도 새 숫자로 바로 풀린다
        cache.set(f"homework:wrong_pin:{self.homework.id}:3", 99, 300)
        self.assertSuccess(self.client.put(url, data={"id": participant.id, "pin": "5678",
                                                      "nickname": "바른이름"}))
        participant.refresh_from_db()
        self.assertEqual((participant.pin, participant.nickname), ("5678", "바른이름"))
        self.assertIsNone(cache.get(f"homework:wrong_pin:{self.homework.id}:3"))

        self.assertSuccess(self.client.delete(url + f"?id={participant.id}"))
        self.assertFalse(HomeworkParticipant.objects.exists())
        self.assertFalse(Submission.objects.exists())

    def test_cannot_touch_other_teachers_participants(self):
        self._guest_submits("3", 0)
        participant = HomeworkParticipant.objects.get()
        self.client.logout()
        self.create_teacher(username="박선생")
        url = self.reverse("teacher_homework_participant_api")
        self.assertFailed(self.client.delete(url + f"?id={participant.id}"))
        self.assertFailed(self.client.get(self.reverse("teacher_homework_submission_api"),
                                          data={"participant_id": participant.id,
                                                "problem_id": self.problem.id}))
        self.assertTrue(HomeworkParticipant.objects.exists())

    # ---- 4단계: 엑셀과 삭제 ----
    def test_excel_has_results_but_no_code(self):
        self._guest_submits("3", -1)
        self._guest_submits("3", 0)
        self._guest_submits("1", -1)
        resp = self.client.get(self.reverse("teacher_homework_board_api"),
                               data={"id": self.homework.id, "download": "1"})
        self.assertEqual(resp["Content-Type"], "application/xlsx")
        self.assertIn(self.homework.code, resp["Content-Disposition"])
        with zipfile.ZipFile(io.BytesIO(resp.content)) as book:
            strings = book.read("xl/sharedStrings.xml").decode("utf-8")
        for text in ("4자리 숫자", "학생3", "1234", "O", "△(1)", "1/1", "0/1"):
            self.assertIn(text, strings)
        self.assertNotIn("print(1)", strings)

    def test_open_homework_cannot_be_deleted(self):
        self._guest_submits("3", 0)
        resp = self.client.delete(self.url + f"?id={self.homework.id}")
        self.assertFailed(resp, "진행 중인 과제는 지울 수 없습니다. 먼저 종료하세요")
        self.assertTrue(Homework.objects.filter(id=self.homework.id).exists())

    def test_deleting_an_ended_homework_removes_every_record(self):
        self._guest_submits("3", 0)
        self.client.put(self.url, data={"id": self.homework.id, "end": True})
        self.assertSuccess(self.client.delete(self.url + f"?id={self.homework.id}"))
        self.assertFalse(Homework.objects.filter(id=self.homework.id).exists())
        self.assertFalse(User.objects.filter(admin_type=AdminType.GUEST).exists())
        self.assertFalse(Submission.objects.exists())
        # 문제는 남는다
        self.assertTrue(Problem.objects.filter(id=self.problem.id).exists())

    def test_cannot_delete_other_teachers_homework(self):
        self.homework.ended_at = now()
        self.homework.save()
        self.client.logout()
        self.create_teacher(username="박선생")
        self.assertFailed(self.client.delete(self.url + f"?id={self.homework.id}"))
        self.assertTrue(Homework.objects.filter(id=self.homework.id).exists())
