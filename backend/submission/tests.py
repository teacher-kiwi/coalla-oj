from copy import deepcopy
from unittest import mock

from problem.models import Problem, ProblemTag
from utils.api.tests import APITestCase
from .models import Submission

DEFAULT_PROBLEM_DATA = {"_id": "A-110", "title": "test", "description": "<p>test</p>", "input_description": "test",
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


# TODO: 대회 제출 테스트 추가


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
