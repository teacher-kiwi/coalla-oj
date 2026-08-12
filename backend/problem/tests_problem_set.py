"""문제집 API 테스트.

핵심은 교차 접근이다. 교사는 자기 문제집과 자기 학급에만, 학생은 자기 학급에
배포된 문제집에만 닿을 수 있어야 한다.
"""
from datetime import timedelta

from django.utils.timezone import now

from account.models import ClassMembership, School
from contest.models import Contest, ContestRuleType
from utils.api.tests import APITestCase

from .models import Problem, ProblemSetAssignment, ProblemSetItem


def create_problem(_id, created_by, contest=None, visible=True):
    return Problem.objects.create(
        _id=_id, title=f"문제 {_id}", description="d", input_description="i",
        output_description="o", samples=[], test_case_id="x", test_case_score=[],
        hint="", languages=["Python3"], template={}, time_limit=1000,
        memory_limit=256, spj=False, rule_type="ACM", visible=visible,
        difficulty="Low", source="", created_by=created_by, contest=contest)


class ProblemSetTestBase(APITestCase):
    def setUp(self):
        self.school = School.objects.create(code="S001", name="코알라초등학교",
                                            kind="초등학교")
        self.teacher = self.create_teacher(username="김선생")
        self.set_url = self.reverse("teacher_problem_set_api")
        self.item_url = self.reverse("teacher_problem_set_problem_api")
        self.assign_url = self.reverse("teacher_problem_set_assignment_api")
        self.problem = create_problem("P1", self.teacher)
        self.problem2 = create_problem("P2", self.teacher)

    def _create_class(self, grade=3, class_no=2):
        return self.client.post(self.reverse("teacher_class_api"), data={
            "school": self.school.id, "year": 2026, "grade": grade,
            "class_no": class_no}).data["data"]["id"]

    def _create_students(self, class_id, a=1, b=2):
        return self.client.post(self.reverse("teacher_student_api"), data={
            "school_class": class_id, "number_from": a, "number_to": b})

    def _create_set(self, title="1주차"):
        return self.client.post(self.set_url, data={"title": title}).data["data"]["id"]

    def _add_problems(self, set_id, problems):
        return self.client.post(self.item_url, data={"problem_set": set_id,
                                                     "problems": problems})

    def _assign(self, set_id, class_id, due_at=None):
        data = {"problem_set": set_id, "school_class": class_id}
        if due_at:
            data["due_at"] = due_at
        return self.client.post(self.assign_url, data=data)


class TeacherProblemSetAPITest(ProblemSetTestBase):
    def test_regular_user_denied(self):
        self.client.logout()
        self.create_user("일반사용자", "pass123")
        self.assertFailed(self.client.get(self.set_url))
        self.assertFailed(self.client.post(self.set_url, data={"title": "몰래"}))

    def test_create_and_list(self):
        resp = self.client.post(self.set_url, data={"title": "1주차", "description": "반복문"})
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["problem_count"], 0)

        listed = self.client.get(self.set_url).data["data"]
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["title"], "1주차")

    def test_edit_and_delete(self):
        set_id = self._create_set()
        self.assertSuccess(self.client.put(self.set_url, data={"id": set_id, "title": "2주차"}))
        self.assertEqual(self.client.get(self.set_url).data["data"][0]["title"], "2주차")
        self.assertSuccess(self.client.delete(self.set_url + f"?id={set_id}"))
        self.assertEqual(self.client.get(self.set_url).data["data"], [])

    def test_add_problems(self):
        set_id = self._create_set()
        resp = self._add_problems(set_id, [self.problem.id, self.problem2.id])
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["added"], 2)

        detail = self.client.get(self.set_url + f"?id={set_id}").data["data"]
        self.assertEqual([i["problem"]["_id"] for i in detail["items"]], ["P1", "P2"])

    def test_duplicate_problem_ignored(self):
        set_id = self._create_set()
        self._add_problems(set_id, [self.problem.id])
        resp = self._add_problems(set_id, [self.problem.id, self.problem2.id])
        self.assertEqual(resp.data["data"]["added"], 1)
        self.assertEqual(ProblemSetItem.objects.filter(problem_set_id=set_id).count(), 2)

    def test_contest_problem_cannot_be_added(self):
        """대회 문제를 담으면 대회 시작 전에 내용이 새어나간다"""
        contest = Contest.objects.create(
            title="교내대회", description="d", real_time_rank=True,
            rule_type=ContestRuleType.ACM, created_by=self.teacher,
            start_time=now(), end_time=now() + timedelta(days=1))
        hidden = create_problem("C1", self.teacher, contest=contest)
        set_id = self._create_set()
        self.assertFailed(self._add_problems(set_id, [hidden.id]))

    def test_reorder(self):
        set_id = self._create_set()
        self._add_problems(set_id, [self.problem.id, self.problem2.id])
        items = self.client.get(self.set_url + f"?id={set_id}").data["data"]["items"]
        reversed_ids = [items[1]["id"], items[0]["id"]]
        self.assertSuccess(self.client.put(self.item_url, data={"problem_set": set_id,
                                                                "items": reversed_ids}))
        detail = self.client.get(self.set_url + f"?id={set_id}").data["data"]
        self.assertEqual([i["problem"]["_id"] for i in detail["items"]], ["P2", "P1"])

    def test_reorder_rejects_stale_list(self):
        set_id = self._create_set()
        self._add_problems(set_id, [self.problem.id, self.problem2.id])
        items = self.client.get(self.set_url + f"?id={set_id}").data["data"]["items"]
        self.assertFailed(self.client.put(self.item_url, data={"problem_set": set_id,
                                                               "items": [items[0]["id"]]}))

    def test_remove_item(self):
        set_id = self._create_set()
        self._add_problems(set_id, [self.problem.id, self.problem2.id])
        item_id = self.client.get(self.set_url + f"?id={set_id}").data["data"]["items"][0]["id"]
        self.assertSuccess(self.client.delete(self.item_url + f"?id={item_id}"))
        self.assertEqual(ProblemSetItem.objects.filter(problem_set_id=set_id).count(), 1)

    def test_assign_to_class(self):
        set_id = self._create_set()
        class_id = self._create_class()
        resp = self._assign(set_id, class_id, due_at="2026-09-01T00:00:00Z")
        self.assertSuccess(resp)

        detail = self.client.get(self.set_url + f"?id={set_id}").data["data"]
        self.assertEqual(len(detail["assignments"]), 1)
        self.assertEqual(detail["assignments"][0]["class_name"],
                         "코알라초등학교 2026학년도 3학년 2반")

        # 같은 학급에 두 번 배포할 수 없다
        self.assertFailed(self._assign(set_id, class_id))

    def test_edit_and_delete_assignment(self):
        set_id = self._create_set()
        class_id = self._create_class()
        assignment_id = self._assign(set_id, class_id).data["data"]["id"]
        self.assertSuccess(self.client.put(self.assign_url,
                                           data={"id": assignment_id, "is_open": False}))
        self.assertFalse(ProblemSetAssignment.objects.get(id=assignment_id).is_open)
        self.assertSuccess(self.client.delete(self.assign_url + f"?id={assignment_id}"))
        self.assertEqual(ProblemSetAssignment.objects.count(), 0)


class ProblemSetCrossAccessTest(ProblemSetTestBase):
    """다른 교사의 문제집·학급에는 어떤 경로로도 닿을 수 없어야 한다"""
    def setUp(self):
        super().setUp()
        self.set_id = self._create_set()
        self._add_problems(self.set_id, [self.problem.id])
        self.class_id = self._create_class()
        self.assignment_id = self._assign(self.set_id, self.class_id).data["data"]["id"]
        self.item_id = self.client.get(
            self.set_url + f"?id={self.set_id}").data["data"]["items"][0]["id"]

        self.client.logout()
        self.other_teacher = self.create_teacher(username="박선생")

    def test_cannot_list_or_read(self):
        self.assertEqual(self.client.get(self.set_url).data["data"], [])
        self.assertFailed(self.client.get(self.set_url + f"?id={self.set_id}"))

    def test_cannot_edit_or_delete(self):
        self.assertFailed(self.client.put(self.set_url, data={"id": self.set_id, "title": "탈취"}))
        self.assertFailed(self.client.delete(self.set_url + f"?id={self.set_id}"))

    def test_cannot_change_problems(self):
        self.assertFailed(self._add_problems(self.set_id, [self.problem2.id]))
        self.assertFailed(self.client.put(self.item_url, data={"problem_set": self.set_id,
                                                               "items": [self.item_id]}))
        self.assertFailed(self.client.delete(self.item_url + f"?id={self.item_id}"))
        self.assertEqual(ProblemSetItem.objects.count(), 1)

    def test_cannot_assign_to_other_teacher_class(self):
        """자기 문제집이어도 남의 학급에는 배포할 수 없다"""
        my_set = self._create_set("남의 반에 배포")
        self.assertFailed(self._assign(my_set, self.class_id))
        self.assertEqual(ProblemSetAssignment.objects.count(), 1)

    def test_cannot_touch_other_assignment(self):
        self.assertFailed(self.client.put(self.assign_url,
                                          data={"id": self.assignment_id, "is_open": False}))
        self.assertFailed(self.client.delete(self.assign_url + f"?id={self.assignment_id}"))
        self.assertTrue(ProblemSetAssignment.objects.get(id=self.assignment_id).is_open)


class StudentProblemSetAPITest(ProblemSetTestBase):
    def setUp(self):
        super().setUp()
        self.set_id = self._create_set()
        self._add_problems(self.set_id, [self.problem.id, self.problem2.id])
        self.class_id = self._create_class()
        self._create_students(self.class_id, 1, 1)
        self.assignment_id = self._assign(self.set_id, self.class_id,
                                          due_at="2026-09-01T00:00:00Z").data["data"]["id"]
        self.student = ClassMembership.objects.get(school_class_id=self.class_id,
                                                   number=1).student
        self.list_url = self.reverse("problem_set_list_api")
        self.detail_url = self.reverse("problem_set_api")

    def _login_student(self, student=None):
        student = student or self.student
        # 학생 로그인 흐름(학교→반→번호+PIN)은 account 쪽에서 검증한다.
        # 여기서는 세션만 필요하므로 비밀번호를 직접 지정한다.
        student.set_password("1234")
        student.save(update_fields=["password"])
        self.client.logout()
        self.client.login(username=student.username, password="1234")

    def test_requires_login(self):
        self.client.logout()
        self.assertFailed(self.client.get(self.list_url))
        self.assertFailed(self.client.get(self.detail_url + f"?id={self.set_id}"))

    def test_list_shows_assigned_set(self):
        self._login_student()
        resp = self.client.get(self.list_url)
        self.assertSuccess(resp)
        data = resp.data["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "1주차")
        self.assertEqual(data[0]["class_name"], "코알라초등학교 2026학년도 3학년 2반")
        self.assertEqual(data[0]["problem_count"], 2)
        self.assertEqual(data[0]["solved_count"], 0)
        self.assertTrue(data[0]["due_at"].startswith("2026-09-01"))

    def test_solved_count(self):
        profile = self.student.userprofile
        profile.acm_problems_status = {"problems": {str(self.problem.id): {"status": 0}}}
        profile.save(update_fields=["acm_problems_status"])
        self._login_student()
        self.assertEqual(self.client.get(self.list_url).data["data"][0]["solved_count"], 1)

    def test_detail(self):
        self._login_student()
        resp = self.client.get(self.detail_url + f"?id={self.set_id}")
        self.assertSuccess(resp)
        self.assertEqual([p["_id"] for p in resp.data["data"]["problems"]], ["P1", "P2"])

    def test_closed_assignment_is_hidden(self):
        ProblemSetAssignment.objects.filter(id=self.assignment_id).update(is_open=False)
        self._login_student()
        self.assertEqual(self.client.get(self.list_url).data["data"], [])
        self.assertFailed(self.client.get(self.detail_url + f"?id={self.set_id}"))

    def test_student_of_other_class_cannot_read(self):
        other_class = self._create_class(grade=4, class_no=1)
        self._create_students(other_class, 1, 1)
        outsider = ClassMembership.objects.get(school_class_id=other_class, number=1).student

        self._login_student(outsider)
        self.assertEqual(self.client.get(self.list_url).data["data"], [])
        self.assertFailed(self.client.get(self.detail_url + f"?id={self.set_id}"))

    def test_regular_user_sees_nothing(self):
        """학급 소속이 없는 개인 학생에게는 문제집이 없다"""
        self.client.logout()
        self.create_user("개인학생", "pass123")
        self.assertEqual(self.client.get(self.list_url).data["data"], [])
        self.assertFailed(self.client.get(self.detail_url + f"?id={self.set_id}"))

    def test_teacher_can_preview_own_set(self):
        """배포 전에도 만든 교사는 내용을 확인할 수 있어야 한다"""
        resp = self.client.get(self.detail_url + f"?id={self.set_id}")
        self.assertSuccess(resp)
        self.assertIsNone(resp.data["data"]["due_at"])
