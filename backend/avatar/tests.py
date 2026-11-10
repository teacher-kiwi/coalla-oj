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
from .models import CoinLog, CoinReason, OwnedItem  # noqa: E402


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


# ---------- 샵 ----------
class ShopTestBase(CoinTestBase):
    def setUp(self):
        super().setUp()
        self.client.login(username="student", password="pass123")
        self.hat = self.item("빨간 비니", "hat", "top", {"head": painted(40, 36)}, 30)
        self.hair = self.item("단발", "hair", "", {"head": painted(40, 36, "b")}, 20)

    def item(self, name, slot, variant, parts, price, visible=True):
        return AvatarItem.objects.create(name=name, slot=slot, variant=variant, parts=parts,
                                         price=price, visible=visible)

    def give(self, amount, ref="x"):
        CoinLog.objects.create(user=self.user, amount=amount, reason="test", ref=ref)

    def buy(self, item):
        return self.client.post(self.reverse("avatar_buy_api"), data={"item_id": item.id})


class BuyTest(ShopTestBase):
    def test_buy_spends_and_wears(self):
        self.give(50)
        resp = self.buy(self.hat)
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"], {"balance": 20, "equipped": {"hat": self.hat.id}})
        log = CoinLog.objects.get(reason=CoinReason.BUY)
        self.assertEqual((log.amount, log.ref), (-30, str(self.hat.id)))
        # 두 번 살 수 없다
        self.assertFailed(self.buy(self.hat))
        self.assertEqual(coins.balance(self.user.id), 20)

    def test_not_enough_coins(self):
        self.give(29)
        self.assertFailed(self.buy(self.hat))
        self.assertFalse(OwnedItem.objects.exists())
        self.assertEqual(coins.balance(self.user.id), 29)

    def test_hidden_item_cannot_be_bought(self):
        self.give(100)
        secret = self.item("비밀", "acc", "", {"head": painted(40, 36)}, 0, visible=False)
        self.assertFailed(self.buy(secret))

    def test_new_item_replaces_same_slot(self):
        self.give(100)
        other = self.item("파란 비니", "hat", "full", {"head": painted(40, 36, "c")}, 10)
        self.buy(self.hat)
        self.buy(self.hair)
        resp = self.buy(other)
        self.assertEqual(resp.data["data"]["equipped"], {"hat": other.id, "hair": self.hair.id})

    def test_guest_cannot_buy(self):
        guest = User.objects.create(username="바로과제1", admin_type=AdminType.GUEST)
        guest.set_password("pw1234")
        guest.save()
        UserProfile.objects.create(user=guest)
        CoinLog.objects.create(user=guest, amount=100, reason="test", ref="x")
        self.client.login(username="바로과제1", password="pw1234")
        self.assertFailed(self.buy(self.hat))

    def test_login_required(self):
        self.client.logout()
        self.assertFailed(self.buy(self.hat))


class ShopListTest(ShopTestBase):
    def test_list_shows_visible_and_owned(self):
        self.give(100)
        self.buy(self.hat)
        self.item("숨김", "acc", "", {"head": painted(40, 36)}, 0, visible=False)
        # 산 뒤에 샵에서 내려도 내 목록에는 남는다
        AvatarItem.objects.filter(id=self.hat.id).update(visible=False)
        data = self.client.get(self.reverse("avatar_shop_api")).data["data"]
        self.assertEqual(sorted(i["name"] for i in data["items"]), ["단발", "빨간 비니"])
        self.assertEqual(data["owned"], [self.hat.id])
        self.assertEqual(data["equipped"], {"hat": self.hat.id})
        self.assertEqual(data["balance"], 70)
        self.assertNotIn("visible", data["items"][0])


class EquipTest(ShopTestBase):
    def equip(self, equip):
        return self.client.put(self.reverse("avatar_equip_api"), data={"equip": equip})

    def test_equip_whole_outfit(self):
        self.give(100)
        self.buy(self.hat)
        self.buy(self.hair)
        resp = self.equip({"hat": None, "hair": self.hair.id})
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["equipped"], {"hair": self.hair.id})
        self.assertEqual(self.equip({}).data["data"]["equipped"], {})

    def test_cannot_wear_unowned_or_wrong_slot(self):
        self.give(100)
        self.buy(self.hat)
        self.assertFailed(self.equip({"hair": self.hair.id}))
        self.assertFailed(self.equip({"hair": self.hat.id}))
        self.assertFailed(self.equip({"wings": self.hat.id}))
        # 실패하면 입은 옷은 그대로
        self.assertEqual(OwnedItem.objects.get().equipped, True)


class LooksTest(ShopTestBase):
    def test_public_looks(self):
        self.give(100)
        self.buy(self.hat)
        self.create_user("plain", "pass123", login=False)
        self.client.logout()
        resp = self.client.get(self.reverse("avatar_looks_api") + "?usernames=student,plain,nobody")
        self.assertSuccess(resp)
        data = resp.data["data"]
        self.assertEqual(data["looks"], {"student": {"hat": self.hat.id}})
        self.assertEqual(list(data["items"]), [self.hat.id])
        self.assertEqual(data["items"][self.hat.id]["parts"]["head"][0], "i")


class CoinLogBuyTitleTest(ShopTestBase):
    def test_buy_row_has_item_name(self):
        self.give(100)
        self.buy(self.hat)
        rows = self.client.get(self.reverse("coin_log_api")).data["data"]["results"]
        self.assertEqual(rows[0]["title"], "빨간 비니")
        self.assertEqual(rows[0]["amount"], -30)


class AdminDeleteOwnedTest(ShopTestBase):
    def test_owned_item_is_hidden_not_deleted(self):
        self.give(100)
        self.buy(self.hat)
        self.create_super_admin()
        url = self.reverse("avatar_item_admin_api")
        resp = self.client.delete(url + f"?id={self.hat.id}")
        self.assertEqual(resp.data["data"], {"hidden": True})
        self.hat.refresh_from_db()
        self.assertFalse(self.hat.visible)
        # 산 사람이 있으면 종류를 바꿀 수 없다
        resp = self.client.put(url, data={**hat_data(variant="full"), "id": self.hat.id})
        self.assertFailed(resp)
        # 아무도 안 산 아이템은 지워진다
        self.assertEqual(self.client.delete(url + f"?id={self.hair.id}").data["data"], {"hidden": False})
        self.assertFalse(AvatarItem.objects.filter(id=self.hair.id).exists())


class SuperAdminWearAllTest(ShopTestBase):
    def setUp(self):
        super().setUp()
        self.client.logout()
        self.root = self.create_super_admin()
        self.secret = self.item("비밀 모자", "hat", "full", {"head": painted(40, 36, "c")}, 999, visible=False)

    def test_sees_and_wears_everything_free(self):
        data = self.client.get(self.reverse("avatar_shop_api")).data["data"]
        self.assertTrue(data["wear_all"])
        self.assertFalse(data["can_buy"])
        self.assertEqual(sorted(data["owned"]), sorted([self.hat.id, self.hair.id, self.secret.id]))
        self.assertEqual(data["hidden"], [self.secret.id])
        resp = self.client.put(self.reverse("avatar_equip_api"), data={"equip": {"hat": self.secret.id, "hair": self.hair.id}})
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["equipped"], {"hat": self.secret.id, "hair": self.hair.id})
        # 코인은 오가지 않고, 사기는 막는다
        self.assertFalse(CoinLog.objects.filter(user=self.root).exists())
        CoinLog.objects.create(user=self.root, amount=100, reason="test", ref="x")
        self.assertFailed(self.buy(self.hat))
        # 슬롯이 맞지 않으면 관리자도 안 된다
        self.assertFailed(self.client.put(self.reverse("avatar_equip_api"), data={"equip": {"hair": self.hat.id}}))

    def test_admin_wearing_does_not_block_delete(self):
        self.client.put(self.reverse("avatar_equip_api"), data={"equip": {"hat": self.secret.id}})
        url = self.reverse("avatar_item_admin_api")
        resp = self.client.put(url, data={**hat_data(name="비밀 모자", variant="top"), "id": self.secret.id})
        self.assertSuccess(resp)
        self.assertFalse(OwnedItem.objects.filter(item=self.secret).exists())
        self.client.put(self.reverse("avatar_equip_api"), data={"equip": {"hat": self.secret.id}})
        self.assertEqual(self.client.delete(url + f"?id={self.secret.id}").data["data"], {"hidden": False})
        self.assertFalse(AvatarItem.objects.filter(id=self.secret.id).exists())
