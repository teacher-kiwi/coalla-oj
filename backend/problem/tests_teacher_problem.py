"""교사 간단 출제 API 테스트.

관리자 출제 화면과 달리 표시 번호·시간 제한·특수 채점을 받지 않고,
테스트케이스를 손으로 입력한다. 새 문제는 비공개로 시작한다.
"""
import json
import os

from django.conf import settings

from account.models import School
from submission.models import Submission
from utils.api.tests import APITestCase

from .models import Problem, ProblemTag, ProblemVisibility
from .serializers import MAX_CASES, MAX_SAMPLE_BYTES, MAX_SAMPLES


def case(input_="1 2", output="3", is_sample=True):
    return {"input": input_, "output": output, "is_sample": is_sample}


class TeacherProblemTestBase(APITestCase):
    def setUp(self):
        School.objects.create(code="S001", name="코알라초등학교", kind="초등학교")
        self.teacher = self.create_teacher(username="김선생")
        self.url = self.reverse("teacher_problem_api")
        self.publish_url = self.reverse("teacher_problem_publish_api")
        for name in ("입출력", "반복"):
            ProblemTag.objects.create(name=name)

    def _create(self, **overrides):
        data = {"title": "두 수의 합", "description": "<p>두 수를 더하세요</p>",
                "input_description": "두 수", "output_description": "합",
                "difficulty": "L1", "tags": ["입출력"],
                "cases": [case("1 2", "3"), case("10 20", "30", is_sample=False)]}
        data.update(overrides)
        return self.client.post(self.url, data=data)


class TeacherProblemCreateTest(TeacherProblemTestBase):
    def test_create_makes_a_private_problem(self):
        resp = self._create()
        self.assertSuccess(resp)
        problem = Problem.objects.get(id=resp.data["data"]["id"])
        self.assertEqual(problem.visibility, ProblemVisibility.private)
        self.assertEqual(problem.created_by, self.teacher)
        # 표시 번호는 서버가 매긴다
        self.assertEqual(problem._id, "1000")

    def test_only_checked_cases_become_samples(self):
        resp = self._create()
        problem = Problem.objects.get(id=resp.data["data"]["id"])
        self.assertEqual(problem.samples, [{"input": "1 2", "output": "3"}])
        # 채점에는 두 개 모두 쓰인다
        self.assertEqual(len(problem.test_case_score), 2)

    def test_test_case_files_are_written(self):
        resp = self._create()
        problem = Problem.objects.get(id=resp.data["data"]["id"])
        test_case_dir = os.path.join(settings.TEST_CASE_DIR, problem.test_case_id)
        with open(os.path.join(test_case_dir, "1.in")) as f:
            self.assertEqual(f.read(), "1 2")
        with open(os.path.join(test_case_dir, "2.out")) as f:
            self.assertEqual(f.read(), "30")
        # 채점 서버가 읽는 info 도 zip 업로드와 같은 모양이어야 한다
        with open(os.path.join(test_case_dir, "info")) as f:
            info = json.load(f)
        self.assertFalse(info["spj"])
        self.assertEqual(sorted(info["test_cases"]), ["1", "2"])
        self.assertIn("stripped_output_md5", info["test_cases"]["1"])

    def test_regular_user_cannot_create(self):
        self.client.logout()
        self.create_user("학생", "test123")
        self.assertFailed(self._create())

    def test_unknown_tag_is_rejected(self):
        self.assertFailed(self._create(tags=["없는태그"]),
                          "등록되지 않은 태그입니다: 없는태그")

    def test_at_least_one_sample_is_required(self):
        self.assertFailed(self._create(cases=[case(is_sample=False)]))

    def test_too_many_samples(self):
        cases = [case(f"{i}", f"{i}") for i in range(MAX_SAMPLES + 1)]
        self.assertFailed(self._create(cases=cases))

    def test_too_many_cases(self):
        cases = [case(f"{i}", f"{i}", is_sample=(i == 0)) for i in range(MAX_CASES + 1)]
        self.assertFailed(self._create(cases=cases))

    def test_sample_size_is_limited(self):
        # 예제는 문제를 여는 모든 학생에게 매번 전송되므로 크기를 제한한다
        big = "x" * (MAX_SAMPLE_BYTES + 1)
        self.assertFailed(self._create(cases=[case(big, "1")]))

    def test_big_case_is_allowed_when_not_a_sample(self):
        big = "x" * (MAX_SAMPLE_BYTES + 1)
        self.assertSuccess(self._create(cases=[case("1", "1"),
                                               case(big, "1", is_sample=False)]))


class TeacherProblemEditTest(TeacherProblemTestBase):
    def setUp(self):
        super().setUp()
        self.problem_id = self._create().data["data"]["id"]

    def _edit(self, **overrides):
        data = {"id": self.problem_id, "title": "바뀐 제목",
                "description": "<p>d</p>", "input_description": "i",
                "output_description": "o", "difficulty": "L3", "tags": ["반복"]}
        data.update(overrides)
        return self.client.put(self.url, data=data)

    def test_edit_without_cases_keeps_test_cases(self):
        before = Problem.objects.get(id=self.problem_id).test_case_id
        self.assertSuccess(self._edit())
        problem = Problem.objects.get(id=self.problem_id)
        self.assertEqual(problem.title, "바뀐 제목")
        self.assertEqual(problem.difficulty, "L3")
        self.assertEqual(problem.test_case_id, before)

    def test_edit_with_cases_replaces_test_cases(self):
        before = Problem.objects.get(id=self.problem_id).test_case_id
        self.assertSuccess(self._edit(cases=[case("5", "5")]))
        problem = Problem.objects.get(id=self.problem_id)
        self.assertNotEqual(problem.test_case_id, before)
        self.assertEqual(problem.samples, [{"input": "5", "output": "5"}])
        self.assertEqual(len(problem.test_case_score), 1)

    def test_other_teacher_cannot_edit(self):
        self.client.logout()
        self.create_teacher(username="박선생")
        self.assertFailed(self._edit(), "문제가 존재하지 않습니다")

    def test_public_problem_cannot_be_edited_by_teacher(self):
        Problem.objects.filter(id=self.problem_id).update(
            visibility=ProblemVisibility.public)
        self.assertFailed(self._edit(), "공개된 문제는 관리자만 수정할 수 있습니다")

    def test_delete(self):
        self.assertSuccess(self.client.delete(self.url + f"?id={self.problem_id}"))
        self.assertFalse(Problem.objects.filter(id=self.problem_id).exists())

    def test_cannot_delete_after_a_submission(self):
        problem = Problem.objects.get(id=self.problem_id)
        Submission.objects.create(user_id=self.teacher.id, problem_id=problem.id,
                                  code="x", language="Python3")
        self.assertFailed(self.client.delete(self.url + f"?id={self.problem_id}"),
                          "이미 제출 기록이 있어 삭제할 수 없습니다")

    def test_other_teacher_cannot_delete(self):
        self.client.logout()
        self.create_teacher(username="박선생")
        self.assertFailed(self.client.delete(self.url + f"?id={self.problem_id}"))


class TeacherProblemListTest(TeacherProblemTestBase):
    def test_list_shows_only_my_problems(self):
        mine = self._create().data["data"]["id"]
        self.client.logout()
        other = self.create_teacher(username="박선생")
        self._create(title="남의 문제")
        self.client.logout()
        self.client.login(username=self.teacher.username, password="teacher")

        resp = self.client.get(self.url)
        self.assertSuccess(resp)
        ids = [p["id"] for p in resp.data["data"]]
        self.assertEqual(ids, [mine])
        self.assertTrue(Problem.objects.filter(created_by=other).exists())

    def test_detail(self):
        problem_id = self._create().data["data"]["id"]
        resp = self.client.get(self.url + f"?id={problem_id}")
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["title"], "두 수의 합")


class ProblemPublishFlowTest(TeacherProblemTestBase):
    def setUp(self):
        super().setUp()
        self.problem_id = self._create().data["data"]["id"]
        self.review_url = self.reverse("problem_publish_review_api")

    def _visibility(self):
        return Problem.objects.get(id=self.problem_id).visibility

    def test_teacher_requests_publish(self):
        self.assertSuccess(self.client.post(self.publish_url, data={"id": self.problem_id}))
        self.assertEqual(self._visibility(), ProblemVisibility.pending)

    def test_cannot_request_twice(self):
        self.client.post(self.publish_url, data={"id": self.problem_id})
        self.assertFailed(self.client.post(self.publish_url, data={"id": self.problem_id}),
                          "이미 공개를 신청했거나 공개된 문제입니다")

    def test_teacher_can_cancel_before_review(self):
        self.client.post(self.publish_url, data={"id": self.problem_id})
        self.assertSuccess(self.client.delete(self.publish_url + f"?id={self.problem_id}"))
        self.assertEqual(self._visibility(), ProblemVisibility.private)

    def test_pending_problem_is_still_hidden_from_the_public_list(self):
        self.client.post(self.publish_url, data={"id": self.problem_id})
        resp = self.client.get(self.reverse("problem_api") + "?limit=100")
        self.assertEqual(resp.data["data"]["results"], [])

    def test_admin_approves(self):
        self.client.post(self.publish_url, data={"id": self.problem_id})
        self.client.logout()
        self.create_super_admin()

        pending = self.client.get(self.review_url)
        self.assertSuccess(pending)
        self.assertEqual([p["id"] for p in pending.data["data"]], [self.problem_id])

        self.assertSuccess(self.client.post(self.review_url,
                                            data={"id": self.problem_id, "approve": True}))
        self.assertEqual(self._visibility(), ProblemVisibility.public)

    def test_admin_rejects_and_teacher_can_fix_and_retry(self):
        self.client.post(self.publish_url, data={"id": self.problem_id})
        self.client.logout()
        self.create_super_admin()
        self.assertSuccess(self.client.post(self.review_url,
                                            data={"id": self.problem_id, "approve": False}))
        # 반려하면 비공개로 돌아가 교사가 고쳐서 다시 신청할 수 있다
        self.assertEqual(self._visibility(), ProblemVisibility.private)

        self.client.logout()
        self.client.login(username=self.teacher.username, password="teacher")
        self.assertSuccess(self.client.post(self.publish_url, data={"id": self.problem_id}))

    def test_teacher_cannot_review(self):
        self.client.post(self.publish_url, data={"id": self.problem_id})
        self.assertFailed(self.client.post(self.review_url,
                                           data={"id": self.problem_id, "approve": True}))

    def test_approved_problem_appears_in_the_public_list(self):
        self.client.post(self.publish_url, data={"id": self.problem_id})
        self.client.logout()
        self.create_super_admin()
        self.client.post(self.review_url, data={"id": self.problem_id, "approve": True})

        resp = self.client.get(self.reverse("problem_api") + "?limit=100")
        self.assertEqual([p["id"] for p in resp.data["data"]["results"]], [self.problem_id])


class AdminEditsTeacherProblemTest(TeacherProblemTestBase):
    """교사가 만든 문제를 관리자가 다루는 경로.

    관리자 문제 목록의 "공개" 스위치는 문제 전체를 다시 저장한다. 그래서 교사 화면에서
    허용한 값(입력 설명 비움 등)을 관리자 직렬화기가 거부하면 스위치조차 눌리지 않는다.
    """
    def setUp(self):
        super().setUp()
        # 입력이 없는 문제. 교사 화면에서는 입력 설명을 비워둘 수 있다.
        self.problem_id = self._create(input_description="", output_description="").data["data"]["id"]
        Problem.objects.filter(id=self.problem_id).update(
            visibility=ProblemVisibility.public)
        self.client.logout()
        self.create_super_admin()
        self.admin_url = self.reverse("problem_admin_api")

    def test_admin_can_toggle_visible_on_a_problem_with_blank_descriptions(self):
        problem = self.client.get(self.admin_url + f"?id={self.problem_id}").data["data"]
        self.assertEqual(problem["input_description"], "")

        # 목록의 스위치는 받은 행을 그대로 되돌려보낸다
        problem["visible"] = False
        resp = self.client.put(self.admin_url, data=problem)
        self.assertSuccess(resp)
        self.assertFalse(Problem.objects.get(id=self.problem_id).visible)

    def test_admin_edit_does_not_reset_visibility(self):
        # 관리자 직렬화기에는 visibility 가 없다. 저장해도 공개 상태가 유지되어야 한다.
        problem = self.client.get(self.admin_url + f"?id={self.problem_id}").data["data"]
        problem["visible"] = False
        self.client.put(self.admin_url, data=problem)
        self.assertEqual(Problem.objects.get(id=self.problem_id).visibility,
                         ProblemVisibility.public)

    def test_admin_edit_keeps_the_original_author(self):
        problem = self.client.get(self.admin_url + f"?id={self.problem_id}").data["data"]
        problem["visible"] = False
        self.client.put(self.admin_url, data=problem)
        self.assertEqual(Problem.objects.get(id=self.problem_id).created_by, self.teacher)
