from django.contrib import auth

from options.options import SysOptions
from utils.api.tests import APITestCase
from .login_throttle import MAX_FAILURES
from .models import ClassMembership, School, SchoolClass, User


class SchoolClassTestBase(APITestCase):
    def setUp(self):
        self.school = School.objects.create(code="S001", name="코알라초등학교",
                                            kind="초등학교", office="전라남도교육청")
        self.teacher = self.create_teacher(username="김선생")
        self.class_url = self.reverse("teacher_class_api")
        self.student_url = self.reverse("teacher_student_api")

    def _create_class(self, prefix="kim3", grade=3, class_no=2):
        return self.client.post(self.class_url, data={
            "school": self.school.id, "year": 2026, "grade": grade,
            "class_no": class_no, "username_prefix": prefix})

    def _create_students(self, class_id, a=1, b=3):
        return self.client.post(self.student_url, data={
            "school_class": class_id, "number_from": a, "number_to": b})


class SchoolClassAPITest(SchoolClassTestBase):
    def test_regular_user_denied(self):
        self.client.logout()
        self.create_user("일반사용자", "pass123")
        self.assertFailed(self.client.get(self.class_url))

    def test_create_class(self):
        resp = self._create_class()
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["display_name"], "2026학년도 3학년 2반")
        self.assertEqual(resp.data["data"]["school_name"], "코알라초등학교")

    def test_duplicate_prefix_rejected(self):
        self._create_class(prefix="kim3")
        resp = self._create_class(prefix="kim3", class_no=3)
        self.assertFailed(resp, "이미 사용 중인 접두사입니다")

    def test_duplicate_class_rejected(self):
        self._create_class(prefix="kim3")
        resp = self._create_class(prefix="kim4")
        self.assertFailed(resp, "같은 학급이 이미 등록되어 있습니다")

    def test_invalid_prefix_rejected(self):
        self.assertFailed(self._create_class(prefix="AB"))       # 대문자·너무 짧음
        self.assertFailed(self._create_class(prefix="한글반"))    # 한글 불가

    def test_other_teacher_cannot_see_or_edit(self):
        class_id = self._create_class().data["data"]["id"]
        self.client.logout()
        self.create_teacher(username="박선생")

        self.assertEqual(self.client.get(self.class_url).data["data"], [])
        self.assertFailed(self.client.get(self.class_url + f"?id={class_id}"))
        self.assertFailed(self.client.put(self.class_url, data={"id": class_id, "grade": 5}))
        self.assertFailed(self.client.delete(self.class_url + f"?id={class_id}"))

    def test_archive_class(self):
        class_id = self._create_class().data["data"]["id"]
        self.assertSuccess(self.client.put(self.class_url,
                                           data={"id": class_id, "is_archived": True}))
        self.assertEqual(self.client.get(self.class_url).data["data"], [])


class StudentAccountAPITest(SchoolClassTestBase):
    def setUp(self):
        super().setUp()
        self.class_id = self._create_class().data["data"]["id"]

    def test_create_students(self):
        resp = self._create_students(self.class_id, 1, 3)
        self.assertSuccess(resp)
        issued = resp.data["data"]["students"]
        self.assertEqual(len(issued), 3)
        # 초기 PIN 은 해시로 저장되므로 생성 직후 응답에서만 평문으로 받는다
        self.assertEqual([s["number"] for s in issued], [1, 2, 3])
        for item in issued:
            self.assertRegex(item["password"], r"^\d{4}$")

        self.assertEqual(ClassMembership.objects.count(), 3)
        student = ClassMembership.objects.get(number=1).student
        self.assertEqual(student.username, "kim3-01")
        self.assertEqual(student.created_by, self.teacher)

    def test_duplicate_number_rejected(self):
        self._create_students(self.class_id, 1, 3)
        self.assertFailed(self._create_students(self.class_id, 2, 4))

    def test_respects_student_limit(self):
        SysOptions.max_students_per_teacher = 2
        resp = self._create_students(self.class_id, 1, 3)
        self.assertFailed(resp)
        self.assertEqual(ClassMembership.objects.count(), 0)
        SysOptions.max_students_per_teacher = 500

    def test_other_teacher_cannot_create_or_list(self):
        self.client.logout()
        self.create_teacher(username="박선생")
        self.assertFailed(self._create_students(self.class_id))
        self.assertFailed(self.client.get(self.student_url + f"?class_id={self.class_id}"))

    def test_reset_password(self):
        self._create_students(self.class_id, 1, 1)
        membership = ClassMembership.objects.get(number=1)
        resp = self.client.put(self.student_url, data={"membership": membership.id})
        self.assertSuccess(resp)
        pin = resp.data["data"]["password"]
        self.assertRegex(pin, r"^\d{4}$")
        self.assertIsNotNone(auth.authenticate(username="kim3-01", password=pin))

    def test_other_teacher_cannot_reset(self):
        self._create_students(self.class_id, 1, 1)
        membership = ClassMembership.objects.get(number=1)
        self.client.logout()
        self.create_teacher(username="박선생")
        self.assertFailed(self.client.put(self.student_url, data={"membership": membership.id}))

    def test_delete_class_removes_students(self):
        self._create_students(self.class_id, 1, 3)
        resp = self.client.delete(self.class_url + f"?id={self.class_id}")
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["deleted_students"], 3)
        self.assertEqual(User.objects.filter(created_by=self.teacher).count(), 0)
        self.assertEqual(SchoolClass.objects.count(), 0)


class StudentLoginAPITest(SchoolClassTestBase):
    def setUp(self):
        super().setUp()
        self.class_id = self._create_class().data["data"]["id"]
        self._create_students(self.class_id, 1, 2)
        # 교사가 알려준 초기 PIN 을 알아내기 위해 초기화 API 를 쓴다
        membership = ClassMembership.objects.get(number=1)
        self.pin = self.client.put(self.student_url,
                                   data={"membership": membership.id}).data["data"]["password"]
        self.client.logout()
        self.login_url = self.reverse("student_login_api")

    def test_search_school(self):
        url = self.reverse("student_school_search_api")
        self.assertFailed(self.client.get(url + "?keyword=코"))     # 두 글자 미만
        resp = self.client.get(url + "?keyword=코알라")
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"][0]["name"], "코알라초등학교")

    def test_search_class_shows_teacher(self):
        url = self.reverse("student_class_search_api")
        resp = self.client.get(url + f"?school_id={self.school.id}")
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"][0]["teacher_name"], "김선생")

    def test_login(self):
        resp = self.client.post(self.login_url, data={
            "school_class": self.class_id, "number": 1, "password": self.pin})
        self.assertSuccess(resp)
        self.assertTrue(auth.get_user(self.client).is_authenticated)

    def test_wrong_password(self):
        wrong = "0000" if self.pin != "0000" else "1111"
        resp = self.client.post(self.login_url, data={
            "school_class": self.class_id, "number": 1, "password": wrong})
        self.assertFailed(resp, "번호 또는 비밀번호가 올바르지 않습니다")

    def test_unknown_number_same_message(self):
        """번호가 없는 경우와 비밀번호가 틀린 경우를 구분해 알려주지 않는다"""
        resp = self.client.post(self.login_url, data={
            "school_class": self.class_id, "number": 99, "password": "1234"})
        self.assertFailed(resp, "번호 또는 비밀번호가 올바르지 않습니다")

    def test_password_must_be_4_digits(self):
        self.assertFailed(self.client.post(self.login_url, data={
            "school_class": self.class_id, "number": 1, "password": "123"}))
        self.assertFailed(self.client.post(self.login_url, data={
            "school_class": self.class_id, "number": 1, "password": "abcd"}))

    def test_lockout_after_repeated_failures(self):
        wrong = "0000" if self.pin != "0000" else "1111"
        for _ in range(MAX_FAILURES):
            self.client.post(self.login_url, data={
                "school_class": self.class_id, "number": 1, "password": wrong})
        # 잠긴 뒤에는 올바른 비밀번호도 거부된다
        resp = self.client.post(self.login_url, data={
            "school_class": self.class_id, "number": 1, "password": self.pin})
        self.assertFailed(resp)
        self.assertIn("잠겼습니다", resp.data["data"])
        self.assertFalse(auth.get_user(self.client).is_authenticated)

    def test_teacher_reset_clears_lockout(self):
        wrong = "0000" if self.pin != "0000" else "1111"
        for _ in range(MAX_FAILURES):
            self.client.post(self.login_url, data={
                "school_class": self.class_id, "number": 1, "password": wrong})

        self.client.login(username="김선생", password="teacher")
        membership = ClassMembership.objects.get(number=1)
        new_pin = self.client.put(self.student_url,
                                  data={"membership": membership.id}).data["data"]["password"]
        self.client.logout()

        resp = self.client.post(self.login_url, data={
            "school_class": self.class_id, "number": 1, "password": new_pin})
        self.assertSuccess(resp)


class StudentChangePasswordTest(SchoolClassTestBase):
    def setUp(self):
        super().setUp()
        self.class_id = self._create_class().data["data"]["id"]
        self._create_students(self.class_id, 1, 1)
        membership = ClassMembership.objects.get(number=1)
        self.pin = self.client.put(self.student_url,
                                   data={"membership": membership.id}).data["data"]["password"]
        self.client.logout()
        self.client.post(self.reverse("student_login_api"), data={
            "school_class": self.class_id, "number": 1, "password": self.pin})
        self.url = self.reverse("student_change_password_api")

    def test_change(self):
        new_pin = "9876" if self.pin != "9876" else "1234"
        resp = self.client.post(self.url, data={"old_password": self.pin,
                                                "new_password": new_pin})
        self.assertSuccess(resp)
        self.assertIsNotNone(auth.authenticate(username="kim3-01", password=new_pin))

    def test_wrong_old_password(self):
        wrong = "0000" if self.pin != "0000" else "1111"
        self.assertFailed(self.client.post(self.url, data={"old_password": wrong,
                                                           "new_password": "9876"}))

    def test_must_be_4_digits(self):
        self.assertFailed(self.client.post(self.url, data={"old_password": self.pin,
                                                           "new_password": "123456"}))

    def test_non_student_rejected(self):
        self.client.logout()
        self.create_user("개인학습자", "pass123")
        self.assertFailed(self.client.post(self.url, data={"old_password": "1234",
                                                           "new_password": "5678"}),
                          "학교에서 발급받은 계정만 사용할 수 있습니다")


class PublicDisplayNameTest(SchoolClassTestBase):
    """학생의 내부 아이디가 공개 화면에 노출되면 안 된다"""
    def setUp(self):
        super().setUp()
        class_id = self._create_class().data["data"]["id"]
        self._create_students(class_id, 1, 1)
        self.student = ClassMembership.objects.get(number=1).student

    def test_student_shows_school_only(self):
        from .models import public_display_name
        self.assertEqual(public_display_name(self.student), "코알라초등학교 학생")
        self.assertNotIn("kim3", public_display_name(self.student))

    def test_google_user_shows_nickname(self):
        from .models import public_display_name
        learner = self.create_user("코딩왕", "pass123", login=False)
        self.assertEqual(public_display_name(learner), "코딩왕")

    def test_submission_list_hides_internal_username(self):
        """제출 목록 경로도 표시 이름을 거쳐야 한다(prefetch 경로 포함)"""
        from problem.models import Problem
        from submission.models import Submission
        problem = Problem.objects.create(
            _id="P1", title="t", description="d", input_description="i",
            output_description="o", samples=[], test_case_id="x", test_case_score=[],
            hint="", languages=["Python3"], template={}, time_limit=1000,
            memory_limit=256, spj=False, rule_type="ACM", visible=True,
            difficulty="Low", source="", created_by=self.teacher)
        Submission.objects.create(problem=problem, user=self.student,
                                  code="print(1)", language="Python3", result=0)

        self.client.logout()
        resp = self.client.get(self.reverse("submission_list_api") + "?limit=10")
        self.assertSuccess(resp)
        names = [r["username"] for r in resp.data["data"]["results"]]
        self.assertIn("코알라초등학교 학생", names)
        self.assertNotIn("kim3-01", names)

    def test_rank_api_hides_internal_username(self):
        self.client.logout()
        resp = self.client.get(self.reverse("user_rank_api") + "?offset=0&limit=10")
        self.assertSuccess(resp)
        for row in resp.data["data"]["results"]:
            self.assertNotIn("kim3", row["user"]["username"])
