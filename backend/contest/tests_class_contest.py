from datetime import timedelta

from django.utils.timezone import now

from account.models import ClassMembership, School
from problem.models import Problem, ProblemVisibility
from utils.api.tests import APITestCase
from .models import ClassContestAssignment, Contest


def make_problem(display_id, created_by, visibility=ProblemVisibility.private, contest=None):
    return Problem.objects.create(
        _id=display_id, title="t", description="d", input_description="i",
        output_description="o", samples=[], test_case_id="x", test_case_score=[],
        hint="", languages=["Python3"], template={}, time_limit=1000,
        memory_limit=256, spj=False, rule_type="ACM", visible=True,
        difficulty="L1", source="", created_by=created_by,
        visibility=visibility, contest=contest)


class ClassContestTestBase(APITestCase):
    def setUp(self):
        self.teacher = self.create_teacher(username="김선생", password="teacher")
        self.school = School.objects.create(code="C1", name="코알라초등학교")
        self.contest_url = self.reverse("teacher_contest_api")
        self.class_url = self.reverse("teacher_contest_class_api")
        self.problem_url = self.reverse("teacher_contest_problem_api")
        self.class_id = self._create_class()

    def _create_class(self, grade=3, class_no=2):
        resp = self.client.post(self.reverse("teacher_class_api"), data={
            "school": self.school.id, "year": 2026, "grade": grade, "class_no": class_no})
        return resp.data["data"]["id"]

    def _create_students(self, class_id, a=1, b=2):
        return self.client.post(self.reverse("teacher_student_api"), data={
            "school_class": class_id, "number_from": a, "number_to": b})

    def _create_contest(self, hours_from_now=1):
        start = now() + timedelta(hours=hours_from_now)
        return self.client.post(self.contest_url, data={
            "title": "1학기 대회", "description": "설명",
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(hours=2)).isoformat()})


class TeacherContestAPITest(ClassContestTestBase):
    def test_create_fixes_class_settings(self):
        """교사는 규칙 유형·비밀번호·IP 제한을 정하지 않는다. 서버가 고정한다."""
        resp = self._create_contest()
        self.assertSuccess(resp)
        contest = Contest.objects.get(id=resp.data["data"]["id"])
        self.assertTrue(contest.is_class_contest)
        self.assertEqual(contest.rule_type, "ACM")
        self.assertTrue(contest.real_time_rank)
        self.assertIsNone(contest.password)
        self.assertEqual(contest.allowed_ip_ranges, [])
        self.assertEqual(contest.created_by, self.teacher)

    def test_end_time_must_follow_start_time(self):
        start = now() + timedelta(hours=1)
        resp = self.client.post(self.contest_url, data={
            "title": "t", "description": "", "start_time": start.isoformat(),
            "end_time": (start - timedelta(hours=1)).isoformat()})
        self.assertFailed(resp)

    def test_other_teacher_cannot_touch_it(self):
        contest_id = self._create_contest().data["data"]["id"]
        self.client.logout()
        self.create_teacher(username="박선생", password="teacher")
        self.assertFailed(self.client.get(self.contest_url + f"?id={contest_id}"),
                          "대회가 존재하지 않습니다")
        self.assertFailed(self.client.delete(self.contest_url + f"?id={contest_id}"),
                          "대회가 존재하지 않습니다")

    def test_underway_contest_cannot_be_deleted(self):
        contest_id = self._create_contest(hours_from_now=-1).data["data"]["id"]
        self.assertFailed(self.client.delete(self.contest_url + f"?id={contest_id}"),
                          "진행 중인 대회는 삭제할 수 없습니다")


class ClassContestVisibilityTest(ClassContestTestBase):
    """학급 대회는 배포받은 학급의 학생과 만든 교사만 볼 수 있다."""
    def setUp(self):
        super().setUp()
        self.contest_id = self._create_contest().data["data"]["id"]
        pin = self._create_students(self.class_id, 1, 1).data["data"]["students"][0]["password"]
        self.student = ClassMembership.objects.get(number=1).student
        self.pin = pin
        self.list_url = self.reverse("contest_list_api")
        self.detail_url = self.reverse("contest_api")

    def _assign(self):
        return self.client.post(self.class_url, data={"contest_id": self.contest_id,
                                                      "class_id": self.class_id})

    def _login_student(self):
        self.client.logout()
        self.client.login(username=self.student.username, password=self.pin)

    def test_hidden_before_assignment(self):
        self._login_student()
        resp = self.client.get(self.list_url + "?limit=10")
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["results"], [])
        self.assertFailed(self.client.get(self.detail_url + f"?id={self.contest_id}"),
                          "대회가 존재하지 않습니다")

    def test_visible_after_assignment(self):
        self.assertSuccess(self._assign())
        self._login_student()
        resp = self.client.get(self.list_url + "?limit=10")
        self.assertSuccess(resp)
        self.assertEqual([c["id"] for c in resp.data["data"]["results"]], [self.contest_id])
        self.assertSuccess(self.client.get(self.detail_url + f"?id={self.contest_id}"))

    def test_hidden_from_outsiders(self):
        self.assertSuccess(self._assign())
        self.client.logout()
        self.create_user("남", "pass123")
        resp = self.client.get(self.list_url + "?limit=10")
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["results"], [])

    def test_admin_contest_is_still_open_to_everyone(self):
        admin = self.create_super_admin(username="root", login=False)
        Contest.objects.create(title="공개 대회", description="d", rule_type="ACM",
                               real_time_rank=True, start_time=now(),
                               end_time=now() + timedelta(days=1), created_by=admin)
        self.client.logout()
        self.create_user("남", "pass123")
        resp = self.client.get(self.list_url + "?limit=10")
        self.assertSuccess(resp)
        self.assertEqual([c["title"] for c in resp.data["data"]["results"]], ["공개 대회"])

    def test_scope_filter_separates_the_two_kinds(self):
        """학생 화면에서 우리 반 대회와 공개 대회를 나눠 볼 수 있어야 한다."""
        admin = self.create_super_admin(username="root", login=False)
        Contest.objects.create(title="공개 대회", description="d", rule_type="ACM",
                               real_time_rank=True, start_time=now(),
                               end_time=now() + timedelta(days=1), created_by=admin)
        self.assertSuccess(self._assign())
        self._login_student()

        def titles(scope):
            resp = self.client.get(self.list_url + f"?limit=10&scope={scope}")
            self.assertSuccess(resp)
            return [c["title"] for c in resp.data["data"]["results"]]

        self.assertEqual(titles("class"), ["1학기 대회"])
        self.assertEqual(titles("public"), ["공개 대회"])
        self.assertEqual(sorted(titles("")), ["1학기 대회", "공개 대회"])

    def test_list_marks_class_contests(self):
        """화면이 배지를 붙일 수 있게 구분값이 응답에 있어야 한다."""
        self.assertSuccess(self._assign())
        self._login_student()
        resp = self.client.get(self.list_url + "?limit=10")
        self.assertSuccess(resp)
        self.assertTrue(resp.data["data"]["results"][0]["is_class_contest"])

    def test_assignment_is_listed_once_per_contest(self):
        """배포 조인 때문에 같은 대회가 여러 번 나오면 안 된다."""
        second = self._create_class(grade=4, class_no=1)
        self.assertSuccess(self._assign())
        self.assertSuccess(self.client.post(self.class_url, data={
            "contest_id": self.contest_id, "class_id": second}))
        resp = self.client.get(self.list_url + "?limit=10")
        self.assertSuccess(resp)
        self.assertEqual(len(resp.data["data"]["results"]), 1)

    def test_other_teacher_class_cannot_be_assigned(self):
        self.client.logout()
        self.create_teacher(username="박선생", password="teacher")
        resp = self.client.post(self.class_url, data={"contest_id": self.contest_id,
                                                      "class_id": self.class_id})
        self.assertFailed(resp, "대회가 존재하지 않습니다")


class ClassContestProblemTest(ClassContestTestBase):
    def setUp(self):
        super().setUp()
        self.contest_id = self._create_contest().data["data"]["id"]

    def test_problem_is_copied_with_a_letter(self):
        mine = make_problem("1000", self.teacher)
        resp = self.client.post(self.problem_url, data={"contest_id": self.contest_id,
                                                        "problem_id": mine.id})
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["_id"], "A")
        # 원본은 그대로 남는다
        mine.refresh_from_db()
        self.assertIsNone(mine.contest_id)
        self.assertEqual(Problem.objects.filter(contest_id=self.contest_id).count(), 1)

    def test_letters_go_in_order(self):
        for i in range(3):
            problem = make_problem(f"200{i}", self.teacher)
            self.client.post(self.problem_url, data={"contest_id": self.contest_id,
                                                     "problem_id": problem.id})
        labels = list(Problem.objects.filter(contest_id=self.contest_id)
                      .order_by("_id").values_list("_id", flat=True))
        self.assertEqual(labels, ["A", "B", "C"])

    def test_cannot_add_another_teachers_private_problem(self):
        self.client.logout()
        other = self.create_teacher(username="박선생", password="teacher")
        theirs = make_problem("3000", other)
        self.client.logout()
        self.client.login(username=self.teacher.username, password="teacher")
        resp = self.client.post(self.problem_url, data={"contest_id": self.contest_id,
                                                        "problem_id": theirs.id})
        self.assertFailed(resp, "문제가 존재하지 않습니다")

    def test_public_problem_can_be_added(self):
        admin = self.create_super_admin(username="root", login=False)
        public = make_problem("4000", admin, visibility=ProblemVisibility.public)
        self.client.login(username=self.teacher.username, password="teacher")
        self.assertSuccess(self.client.post(self.problem_url, data={
            "contest_id": self.contest_id, "problem_id": public.id}))

    def test_cannot_change_problems_after_start(self):
        started = self._create_contest(hours_from_now=-1).data["data"]["id"]
        mine = make_problem("5000", self.teacher)
        self.assertFailed(self.client.post(self.problem_url, data={
            "contest_id": started, "problem_id": mine.id}),
            "시작한 대회에는 문제를 넣을 수 없습니다")

    def test_removing_a_problem_keeps_the_original(self):
        mine = make_problem("6000", self.teacher)
        copy_id = self.client.post(self.problem_url, data={
            "contest_id": self.contest_id, "problem_id": mine.id}).data["data"]["id"]
        self.assertSuccess(self.client.delete(
            self.problem_url + f"?contest_id={self.contest_id}&problem_id={copy_id}"))
        self.assertFalse(Problem.objects.filter(id=copy_id).exists())
        self.assertTrue(Problem.objects.filter(id=mine.id).exists())


class ClassContestAssignmentModelTest(ClassContestTestBase):
    def test_deleting_contest_removes_assignments(self):
        contest_id = self._create_contest().data["data"]["id"]
        self.client.post(self.class_url, data={"contest_id": contest_id,
                                               "class_id": self.class_id})
        self.assertEqual(ClassContestAssignment.objects.count(), 1)
        self.assertSuccess(self.client.delete(self.contest_url + f"?id={contest_id}"))
        self.assertEqual(ClassContestAssignment.objects.count(), 0)
