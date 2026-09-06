from copy import deepcopy
from datetime import timedelta
from unittest import mock

from django.utils.timezone import now

from contest.models import Contest
from contest.tests import DEFAULT_CONTEST_DATA
from problem.models import ContestProblem, Problem, ProblemTag
from utils.api.tests import APITestCase
from .models import Submission
from .views.oj import SubmissionAPI

DEFAULT_PROBLEM_DATA = {"title": "test", "description": "<p>test</p>", "input_description": "test",
                        "output_description": "test", "time_limit": 1000, "memory_limit": 256, "difficulty": "L1",
                        "visible": True, "tags": ["test"], "languages": ["C", "C++", "Java", "Python2"], "template": {},
                        "samples": [{"input": "test", "output": "test"}], "spj": False, "spj_language": "C",
                        "spj_code": "", "test_case_id": "499b26290cc7994e0b497212e842ea85",
                        "test_case_score": [{"output_name": "1.out", "input_name": "1.in", "output_size": 0,
                                             "stripped_output_md5": "d41d8cd98f00b204e9800998ecf8427e",
                                             "input_size": 0, "score": 0}],
                        "rule_type": "ACM", "hint": "<p>test</p>", "source": "test"}

DEFAULT_SUBMISSION_DATA = {
    "problem_id": "1",
    "code": "xxxxxxxxxxxxxx",
    "result": -2,
    "info": {},
    "language": "C",
    "statistic_info": {}
}


class SubmissionPrepare(APITestCase):
    def _create_problem_and_submission(self):
        user = self.create_admin("test", "test123", login=False)
        problem_data = deepcopy(DEFAULT_PROBLEM_DATA)
        tags = problem_data.pop("tags")
        problem_data["created_by"] = user
        self.problem = Problem.objects.create(**problem_data)
        for tag in tags:
            tag = ProblemTag.objects.create(name=tag)
            self.problem.tags.add(tag)
        self.problem.save()
        self.submission_data = deepcopy(DEFAULT_SUBMISSION_DATA)
        self.submission_data["problem_id"] = self.problem.id
        self.submission_data["user_id"] = user.id
        self.submission = Submission.objects.create(**self.submission_data)


class SubmissionListTest(SubmissionPrepare):
    def setUp(self):
        self._create_problem_and_submission()
        self.create_user("123", "345")
        self.url = self.reverse("submission_list_api")

    def test_get_submission_list(self):
        resp = self.client.get(self.url, data={"limit": "10"})
        self.assertSuccess(resp)

    def test_list_carries_both_the_number_and_the_title(self):
        """목록에는 제목을 보여주고, 번호는 문제로 이동할 때 쓴다."""
        resp = self.client.get(self.url, data={"limit": "10"})
        self.assertSuccess(resp)
        row = resp.data["data"]["results"][0]
        self.assertEqual(row["problem"], self.problem.display_id)
        self.assertEqual(row["problem_title"], self.problem.title)

    def test_filter_by_problem_number(self):
        """주소에 들어오는 문제 번호는 pk 다."""
        resp = self.client.get(self.url, data={"limit": "10", "problem_id": self.problem.id})
        self.assertSuccess(resp)
        self.assertEqual(len(resp.data["data"]["results"]), 1)

    def test_unreadable_problem_number_is_not_an_error(self):
        # 번호를 그대로 조회에 넘기면 500 이 난다
        for value in ("abc", "-1", "99999999999999999999"):
            self.assertFailed(self.client.get(self.url, data={"limit": "10", "problem_id": value}),
                              "문제가 존재하지 않습니다")


class ContestSubmissionListTest(APITestCase):
    """대회 제출 목록은 대회 안 표시(A, B, C)로 거른다."""
    def setUp(self):
        self.admin = self.create_admin("teacher", "test123")
        contest_data = deepcopy(DEFAULT_CONTEST_DATA)
        contest_data["password"] = ""
        contest_data["start_time"] = str(now() - timedelta(hours=1))
        contest_data["end_time"] = str(now() + timedelta(hours=1))
        self.contest = self.client.post(self.reverse("contest_admin_api"),
                                        data=contest_data).data["data"]
        problem_data = deepcopy(DEFAULT_PROBLEM_DATA)
        problem_data.pop("tags")
        problem_data["created_by"] = self.admin
        self.problem = Problem.objects.create(**problem_data)
        ContestProblem.objects.create(contest_id=self.contest["id"], problem=self.problem, order=1)
        self.submission = Submission.objects.create(
            problem=self.problem, contest_id=self.contest["id"], user=self.admin,
            code="x", language="C", result=-2)
        self.url = self.reverse("contest_submission_list_api")

    def _get(self, **params):
        params.setdefault("limit", "10")
        params["contest_id"] = self.contest["id"]
        return self.client.get(self.url, data=params)

    def test_filter_by_label(self):
        resp = self._get(problem_id="A")
        self.assertSuccess(resp)
        self.assertEqual(len(resp.data["data"]["results"]), 1)

    def test_unreadable_label_is_not_an_error(self):
        for value in ("abc", "가", "-1"):
            self.assertFailed(self._get(problem_id=value), "문제가 존재하지 않습니다")


class SubmissionThrottlingTest(APITestCase):
    """제출 빈도 제한. 실제 토큰버킷은 레디스를 쓰므로 결과만 흉내낸다."""
    def setUp(self):
        self.user = self.create_user("student", "test123")
        self.request = mock.MagicMock()
        self.request.user = self.user

    @mock.patch("submission.views.oj.TokenBucket")
    def test_allowed_returns_nothing(self, bucket):
        bucket.return_value.consume.return_value = (True, 0)
        self.assertIsNone(SubmissionAPI().throttling(self.request))

    @mock.patch("submission.views.oj.TokenBucket")
    def test_blocked_message_is_korean(self, bucket):
        bucket.return_value.consume.return_value = (False, 12.7)
        message = SubmissionAPI().throttling(self.request)
        self.assertEqual(message, "제출이 너무 잦습니다. 12초 후에 다시 시도해주세요")

    @mock.patch("submission.views.oj.TokenBucket")
    def test_bucket_is_per_account(self, bucket):
        """IP 단위로 세면 한 교실 30명이 같은 공인 IP 를 써서 함께 막힌다."""
        bucket.return_value.consume.return_value = (True, 0)
        SubmissionAPI().throttling(self.request)
        self.assertEqual(bucket.call_args.kwargs["key"], str(self.user.id))


class SubmissionExistsScopeTest(APITestCase):
    """이 문제에 제출한 적이 있는지는 묻는 자리마다 범위가 다르다."""
    def setUp(self):
        self.admin = self.create_admin("teacher", "test123", login=False)
        problem_data = deepcopy(DEFAULT_PROBLEM_DATA)
        problem_data.pop("tags")
        problem_data["created_by"] = self.admin
        self.problem = Problem.objects.create(**problem_data)
        self.contest = Contest.objects.create(
            title="c", description="d", rule_type="ACM", real_time_rank=True,
            start_time=now() - timedelta(hours=1), end_time=now() + timedelta(hours=1),
            created_by=self.admin)
        ContestProblem.objects.create(contest=self.contest, problem=self.problem, order=1)
        self.student = self.create_user("student", "test123")
        self.url = self.reverse("submission_exists")

    def _ask(self, contest=None):
        params = {"problem_id": self.problem.id}
        if contest is not None:
            params["contest_id"] = contest.id
        return self.client.get(self.url, data=params).data["data"]

    def test_solving_outside_does_not_count_inside_the_contest(self):
        Submission.objects.create(problem=self.problem, user=self.student, code="x",
                                  language="C", result=0)
        self.assertTrue(self._ask())
        self.assertFalse(self._ask(self.contest))

    def test_submitting_inside_counts_inside(self):
        Submission.objects.create(problem=self.problem, user=self.student,
                                  contest=self.contest, code="x", language="C", result=0)
        self.assertTrue(self._ask(self.contest))

    def test_running_contest_submission_does_not_count_outside(self):
        Submission.objects.create(problem=self.problem, user=self.student,
                                  contest=self.contest, code="x", language="C", result=0)
        self.assertFalse(self._ask())

    def test_unreadable_problem_number_is_not_an_error(self):
        resp = self.client.get(self.url, data={"problem_id": "99999999999999999999"})
        self.assertFailed(resp)


class ContestSubmissionsJoinPublicListTest(APITestCase):
    """대회가 끝나면 그 제출이 공개 목록에 함께 나온다.

    합쳤다는 표시를 저장하지 않고 끝 시각으로 그때그때 판단한다. 대회를 다시
    열면(끝 시각을 미루면) 도로 숨고, 되돌릴 상태가 남지 않는다.
    """
    def setUp(self):
        self.admin = self.create_admin("teacher", "test123")
        problem_data = deepcopy(DEFAULT_PROBLEM_DATA)
        problem_data.pop("tags")
        problem_data["created_by"] = self.admin
        self.problem = Problem.objects.create(**problem_data)
        self.contest = Contest.objects.create(
            title="c", description="d", rule_type="ACM", real_time_rank=True,
            start_time=now() - timedelta(hours=2), end_time=now() + timedelta(hours=1),
            created_by=self.admin)
        ContestProblem.objects.create(contest=self.contest, problem=self.problem, order=1)
        Submission.objects.create(problem=self.problem, contest=self.contest, user=self.admin,
                                  code="x", language="C", result=-2)
        self.url = self.reverse("submission_list_api")

    def _public_count(self):
        resp = self.client.get(self.url, data={"limit": "10"})
        self.assertSuccess(resp)
        return len(resp.data["data"]["results"])

    def test_hidden_while_the_contest_runs(self):
        self.assertEqual(self._public_count(), 0)

    def test_shown_after_the_contest_ends(self):
        Contest.objects.filter(id=self.contest.id).update(end_time=now() - timedelta(minutes=1))
        self.assertEqual(self._public_count(), 1)

    def test_hidden_again_when_the_contest_is_extended(self):
        Contest.objects.filter(id=self.contest.id).update(end_time=now() - timedelta(minutes=1))
        self.assertEqual(self._public_count(), 1)
        Contest.objects.filter(id=self.contest.id).update(end_time=now() + timedelta(hours=1))
        self.assertEqual(self._public_count(), 0)


@mock.patch("submission.views.oj.judge_task.send")
class SubmissionAPITest(SubmissionPrepare):
    def setUp(self):
        self._create_problem_and_submission()
        self.user = self.create_user("123", "test123")
        self.url = self.reverse("submission_api")

    def test_create_submission(self, judge_task):
        resp = self.client.post(self.url, self.submission_data)
        self.assertSuccess(resp)
        judge_task.assert_called()

    def test_create_submission_with_wrong_language(self, judge_task):
        self.submission_data.update({"language": "Python3"})
        resp = self.client.post(self.url, self.submission_data)
        self.assertFailed(resp)
        self.assertDictEqual(resp.data, {"error": "error",
                                         "data": "Python3 언어는 이 문제에서 사용할 수 없습니다"})
        judge_task.assert_not_called()


class SubmissionDetailPermissionTest(SubmissionPrepare):
    """제출 코드를 누가 볼 수 있는지.

    학생 코드가 다른 학생에게 새어나가면 그대로 커닝 통로가 된다.
    """
    def setUp(self):
        self._create_problem_and_submission()
        self.url = self.reverse("submission_api")

    def test_owner_can_read_own_submission(self):
        # 제출은 create_admin("test") 이 만든 것이다
        self.client.login(username="test", password="test123")
        resp = self.client.get(self.url + "?id=" + self.submission.id)
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["id"], self.submission.id)

    def test_other_user_cannot_read(self):
        self.create_user("other", "test123")
        self.assertFailed(self.client.get(self.url + "?id=" + self.submission.id),
                          "이 제출 기록에 접근할 권한이 없습니다")

    def test_super_admin_can_read(self):
        self.create_super_admin("root2", "test123")
        self.assertSuccess(self.client.get(self.url + "?id=" + self.submission.id))

    def test_anonymous_is_rejected(self):
        self.client.logout()
        resp = self.client.get(self.url + "?id=" + self.submission.id)
        self.assertFailed(resp)

    def test_missing_id(self):
        self.create_user("other2", "test123")
        self.assertFailed(self.client.get(self.url), "잘못된 요청입니다. id가 필요합니다")
