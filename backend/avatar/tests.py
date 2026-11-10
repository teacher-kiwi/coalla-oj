from utils.api.tests import APITestCase

from .models import AvatarItem


def blank(w, h):
    return "." * (w * h)


def painted(w, h, ch="i"):
    text = blank(w, h)
    return ch + text[1:]


def hat_data(**overrides):
    data = {"name": "빨간 비니", "slot": "hat", "variant": "top",
            "parts": {"head": painted(40, 36)}, "price": 40, "visible": False, "designer": ""}
    data.update(overrides)
    return data


class AvatarItemAdminAPITest(APITestCase):
    def setUp(self):
        self.url = self.reverse("avatar_item_admin_api")
        self.create_super_admin()

    def test_create_and_list(self):
        resp = self.client.post(self.url, data=hat_data())
        self.assertSuccess(resp)
        item = AvatarItem.objects.get()
        self.assertEqual(item.variant, "top")
        self.assertEqual(item.parts["head"][0], "i")
        resp = self.client.get(self.url)
        self.assertSuccess(resp)
        self.assertEqual([i["name"] for i in resp.data["data"]], ["빨간 비니"])

    def test_variant_defaults_to_first_choice(self):
        resp = self.client.post(self.url, data=hat_data(variant=""))
        self.assertSuccess(resp)
        self.assertEqual(AvatarItem.objects.get().variant, "top")

    def test_rejects_wrong_variant(self):
        self.assertFailed(self.client.post(self.url, data=hat_data(variant="pants")))
        # 종류가 없는 자리에 종류를 적어도 안 된다
        self.assertFailed(self.client.post(self.url, data=hat_data(slot="hair", variant="top")))

    def test_parts_must_match_slot(self):
        # 치마는 skirt 한 부위, 바지는 양 다리
        skirt = {"skirt": painted(26, 16)}
        self.assertSuccess(self.client.post(self.url, data=hat_data(slot="bottom", variant="skirt", parts=skirt)))
        self.assertFailed(self.client.post(self.url, data=hat_data(slot="bottom", variant="pants", parts=skirt)))
        legs = {"legL": painted(11, 16), "legR": blank(11, 16)}
        self.assertSuccess(self.client.post(self.url, data=hat_data(slot="bottom", variant="pants", parts=legs)))

    def test_rejects_wrong_size_or_letters(self):
        self.assertFailed(self.client.post(self.url, data=hat_data(parts={"head": "i" * 10})))
        bad = "#" + blank(40, 36)[1:]
        self.assertFailed(self.client.post(self.url, data=hat_data(parts={"head": bad})))

    def test_rejects_empty_drawing(self):
        self.assertFailed(self.client.post(self.url, data=hat_data(parts={"head": blank(40, 36)})))

    def test_rejects_blank_name(self):
        self.assertFailed(self.client.post(self.url, data=hat_data(name="   ")))

    def test_update_and_delete(self):
        self.client.post(self.url, data=hat_data())
        item = AvatarItem.objects.get()
        resp = self.client.put(self.url, data={**hat_data(price=99, visible=True), "id": item.id})
        self.assertSuccess(resp)
        item.refresh_from_db()
        self.assertEqual((item.price, item.visible), (99, True))
        self.assertSuccess(self.client.delete(self.url + f"?id={item.id}"))
        self.assertFalse(AvatarItem.objects.exists())

    def test_update_missing_item(self):
        self.assertFailed(self.client.put(self.url, data={**hat_data(), "id": 999}))

    def test_only_super_admin(self):
        for login in (self.create_admin, self.create_teacher, lambda: self.create_user("s", "s")):
            self.client.logout()
            login()
            # 관리자가 아니면 미들웨어가(login-required), 일반 관리자는 데코레이터가 막는다
            self.assertFailed(self.client.post(self.url, data=hat_data()))
            self.assertFailed(self.client.get(self.url))
        self.assertFalse(AvatarItem.objects.exists())


# ---------- 코인 ----------
from copy import deepcopy  # noqa: E402
from datetime import timedelta  # noqa: E402
from unittest import mock  # noqa: E402

from django.utils.timezone import now  # noqa: E402

from account.models import AdminType, User, UserProfile  # noqa: E402
from contest.models import Contest  # noqa: E402
from judge.dispatcher import JudgeDispatcher  # noqa: E402
from judge.tests import DEFAULT_PROBLEM_DATA, case  # noqa: E402
from problem.models import ContestProblem, Problem  # noqa: E402
from submission.models import JudgeStatus, Submission  # noqa: E402
from utils.constants import ContestRuleType  # noqa: E402

from . import coins  # noqa: E402
from .models import CoinLog, CoinReason  # noqa: E402


class CoinTestBase(APITestCase):
    def setUp(self):
        self.user = self.create_user("student", "pass123", login=False)
        self.problem = self.make_problem()

    def make_problem(self):
        data = deepcopy(DEFAULT_PROBLEM_DATA)
        data["created_by"] = self.user
        return Problem.objects.create(**data)

    def submit(self, problem=None, contest=None, user=None):
        return Submission.objects.create(user_id=(user or self.user).id, problem_id=(problem or self.problem).id,
                                         code="print(1)", language="Python3", contest=contest,
                                         result=JudgeStatus.PENDING, info={}, statistic_info={})

    def judge(self, submission, results):
        """채점 서버만 가짜로 두고 실제 judge() 를 돌린다"""
        server = mock.MagicMock(service_url="http://judge")
        choose = mock.MagicMock()
        choose.return_value.__enter__.return_value = server
        resp = {"err": None, "data": [dict(case(r), test_case=str(i + 1)) for i, r in enumerate(results)]}
        with mock.patch("judge.dispatcher.ChooseJudgeServer", choose), \
                mock.patch.object(JudgeDispatcher, "_request", return_value=resp), \
                mock.patch("judge.dispatcher.process_pending_task"):
            JudgeDispatcher(submission.id, submission.problem_id).judge()


class SolveCoinTest(CoinTestBase):
    def test_first_accept_gives_ten_once(self):
        first = self.submit()
        self.judge(first, [JudgeStatus.ACCEPTED])
        self.assertEqual(coins.balance(self.user.id), 10)
        log = CoinLog.objects.get()
        self.assertEqual((log.reason, log.ref, log.submission_id), (CoinReason.SOLVE, str(self.problem.id), first.id))
        # 같은 문제를 또 맞혀도 다시 주지 않는다
        self.judge(self.submit(), [JudgeStatus.ACCEPTED])
        self.assertEqual(coins.balance(self.user.id), 10)
        # 다른 문제는 또 준다
        self.judge(self.submit(problem=self.make_problem()), [JudgeStatus.ACCEPTED])
        self.assertEqual(coins.balance(self.user.id), 20)

    def test_wrong_answer_gives_nothing(self):
        self.judge(self.submit(), [JudgeStatus.WRONG_ANSWER])
        self.assertEqual(coins.balance(self.user.id), 0)

    def test_coin_exists_before_result_is_visible(self):
        # 화면은 결과가 저장되자마자 제출을 다시 읽는다. 그때 코인이 이미 있어야 한다.
        submission = self.submit()
        seen = []
        original = Submission.save

        def spy(obj, *args, **kwargs):
            if obj.result == JudgeStatus.ACCEPTED:
                seen.append(CoinLog.objects.filter(submission_id=obj.id).exists())
            return original(obj, *args, **kwargs)
        with mock.patch.object(Submission, "save", spy):
            self.judge(submission, [JudgeStatus.ACCEPTED])
        self.assertTrue(seen and all(seen))

    def test_contest_submission_gives_nothing(self):
        contest = Contest.objects.create(title="c", description="d", start_time=now() - timedelta(hours=1),
                                         end_time=now() + timedelta(hours=1), rule_type=ContestRuleType.ACM,
                                         password="", created_by=self.user, visible=True, real_time_rank=True)
        ContestProblem.objects.create(contest=contest, problem=self.problem, order=1)
        other = self.create_user("other", "pass123", login=False)
        self.judge(self.submit(contest=contest, user=other), [JudgeStatus.ACCEPTED])
        self.assertFalse(CoinLog.objects.exists())

    def test_homework_guest_gives_nothing(self):
        guest = User.objects.create(username="바로과제1", admin_type=AdminType.GUEST)
        UserProfile.objects.create(user=guest)
        self.judge(self.submit(user=guest), [JudgeStatus.ACCEPTED])
        self.assertFalse(CoinLog.objects.exists())

    def test_submission_detail_shows_coins_to_owner(self):
        submission = self.submit()
        self.judge(submission, [JudgeStatus.ACCEPTED])
        self.client.login(username="student", password="pass123")
        resp = self.client.get(self.reverse("submission_api") + f"?id={submission.id}")
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["coins"], 10)


class AttendanceCoinTest(CoinTestBase):
    def setUp(self):
        super().setUp()
        self.client.login(username="student", password="pass123")
        self.url = self.reverse("user_profile_api")

    def test_once_a_day(self):
        resp = self.client.get(self.url)
        self.assertEqual((resp.data["data"]["coin_notice"], resp.data["data"]["coins"]), (5, 5))
        resp = self.client.get(self.url)
        self.assertEqual((resp.data["data"]["coin_notice"], resp.data["data"]["coins"]), (0, 5))
        # 다음 날(한국 날짜)이면 또 준다
        with mock.patch("avatar.coins.today", return_value="2099-01-01"):
            resp = self.client.get(self.url)
        self.assertEqual(resp.data["data"]["coins"], 10)

    def test_other_profile_does_not_count(self):
        self.create_user("other", "pass123", login=False)
        resp = self.client.get(self.url + "?username=other")
        self.assertNotIn("coins", resp.data["data"])
        self.assertFalse(CoinLog.objects.exists())

    def test_anonymous_gets_nothing(self):
        self.client.logout()
        self.assertSuccess(self.client.get(self.url))
        self.assertFalse(CoinLog.objects.exists())


class CoinLogAPITest(CoinTestBase):
    def test_history_with_titles(self):
        self.judge(self.submit(), [JudgeStatus.ACCEPTED])
        self.client.login(username="student", password="pass123")
        self.client.get(self.reverse("user_profile_api"))  # 출석 5
        resp = self.client.get(self.reverse("coin_log_api"))
        self.assertSuccess(resp)
        data = resp.data["data"]
        self.assertEqual(data["balance"], 15)
        self.assertEqual(data["total"], 2)
        self.assertEqual([r["reason"] for r in data["results"]], ["attend", "solve"])
        self.assertEqual(data["results"][1]["title"], "test")

    def test_login_required(self):
        self.assertFailed(self.client.get(self.reverse("coin_log_api")))


class PastSolveCoinCommandTest(CoinTestBase):
    def test_backfill_practice_only_once(self):
        from django.core.management import call_command
        profile = self.user.userprofile
        other = self.make_problem()
        profile.acm_problems_status = {
            "problems": {str(self.problem.id): {"status": 0}, str(other.id): {"status": -1}},
            # 대회 안에서만 푼 문제는 주지 않는다
            "contest_problems": {"1": {"999": {"status": 0}}}}
        profile.save()
        call_command("grant_past_solve_coins", stdout=mock.MagicMock())
        self.assertFalse(CoinLog.objects.exists())
        call_command("grant_past_solve_coins", "--apply", stdout=mock.MagicMock())
        call_command("grant_past_solve_coins", "--apply", stdout=mock.MagicMock())
        self.assertEqual(list(CoinLog.objects.values_list("ref", "amount")), [(str(self.problem.id), 10)])
