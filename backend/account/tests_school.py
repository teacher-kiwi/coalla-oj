from unittest import mock

from django.contrib import auth

from options.options import SysOptions
from utils.api.tests import APITestCase
from .login_throttle import MAX_FAILURES, clear_login_failures
from .models import ClassMembership, School, SchoolClass, User


class SchoolClassTestBase(APITestCase):
    def _clear_throttle(self, class_id, upto=100):
        """로그인 실패 카운터는 Redis 에 있어 테스트 롤백으로 지워지지 않는다.
        테스트 간 상태가 새지 않도록 명시적으로 비운다."""
        for number in range(1, upto + 1):
            clear_login_failures(class_id, number)

    def setUp(self):
        self.school = School.objects.create(code="S001", name="코알라초등학교",
                                            kind="초등학교", office="전라남도교육청")
        self.teacher = self.create_teacher(username="김선생")
        self.class_url = self.reverse("teacher_class_api")
        self.student_url = self.reverse("teacher_student_api")
        self.sheet_url = self.reverse("teacher_student_sheet_api")

    def _create_class(self, grade=3, class_no=2):
        resp = self.client.post(self.class_url, data={
            "school": self.school.id, "year": 2026, "grade": grade,
            "class_no": class_no})
        if resp.data.get("error") is None:
            self._clear_throttle(resp.data["data"]["id"])
        return resp

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

    def test_username_is_generated(self):
        """아이디는 교사가 정하지 않고 학급 id 로 자동 생성된다"""
        class_id = self._create_class().data["data"]["id"]
        self._create_students(class_id, 1, 1)
        self.assertTrue(User.objects.filter(username=f"c{class_id}-01").exists())

    def test_duplicate_class_rejected(self):
        self._create_class()
        resp = self._create_class()
        self.assertFailed(resp, "같은 학급이 이미 등록되어 있습니다")

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
        self.assertEqual(student.username, f"c{self.class_id}-01")
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
        self.assertIsNotNone(auth.authenticate(username=f"c{self.class_id}-01", password=pin))

    def test_other_teacher_cannot_reset(self):
        self._create_students(self.class_id, 1, 1)
        membership = ClassMembership.objects.get(number=1)
        self.client.logout()
        self.create_teacher(username="박선생")
        self.assertFailed(self.client.put(self.student_url, data={"membership": membership.id}))

    def test_delete_student(self):
        self._create_students(self.class_id, 1, 2)
        membership = ClassMembership.objects.get(number=1)
        student_id = membership.student_id

        self.assertSuccess(self.client.delete(self.student_url + f"?id={membership.id}"))
        # 계정과 소속이 함께 사라진다
        self.assertFalse(User.objects.filter(id=student_id).exists())
        self.assertFalse(ClassMembership.objects.filter(id=membership.id).exists())
        # 같은 학급의 다른 학생은 그대로 있다
        self.assertEqual(ClassMembership.objects.filter(school_class_id=self.class_id).count(), 1)

    def test_other_teacher_cannot_delete_student(self):
        # 학생 삭제는 제출 기록까지 함께 지우는 되돌릴 수 없는 동작이다.
        # 남의 반 학생에게 절대 닿으면 안 된다.
        self._create_students(self.class_id, 1, 1)
        membership = ClassMembership.objects.get(number=1)
        self.client.logout()
        self.create_teacher(username="박선생")

        self.assertFailed(self.client.delete(self.student_url + f"?id={membership.id}"),
                          "학생이 존재하지 않습니다")
        self.assertTrue(ClassMembership.objects.filter(id=membership.id).exists())

    def test_delete_student_rejects_non_numeric_id(self):
        # 쿼리스트링으로 온 id 를 그대로 조회하면 ValueError 로 500 이 난다
        self.assertFailed(self.client.delete(self.student_url + "?id=abc"),
                          "잘못된 요청입니다. id가 필요합니다")

    def test_download_account_sheet(self):
        # 학기 초에 교사가 아이디·PIN 을 배부할 때 쓰는 경로다.
        # 파일은 한 번 내려받으면 지워지므로 두 번째 요청은 실패해야 한다.
        resp = self._create_students(self.class_id, 1, 2)
        file_id = resp.data["data"]["file_id"]

        downloaded = self.client.get(self.sheet_url + f"?file_id={file_id}")
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded["Content-Type"], "application/xlsx")
        self.assertTrue(downloaded.content)

        self.assertFailed(self.client.get(self.sheet_url + f"?file_id={file_id}"),
                          "파일이 존재하지 않습니다")

    def test_account_sheet_rejects_bad_file_id(self):
        # file_id 가 그대로 경로에 들어가므로 형태를 반드시 검사해야 한다
        for bad in ("", "../../etc/passwd", "a b"):
            self.assertFailed(self.client.get(self.sheet_url + f"?file_id={bad}"),
                              "잘못된 요청입니다")

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
        self.assertIsNotNone(auth.authenticate(username=f"c{self.class_id}-01", password=new_pin))
        # 세션을 끊어 화면이 "다시 로그인" 안내를 띄울 수 있게 한다
        self.assertFailed(self.client.post(self.url, data={"old_password": new_pin,
                                                           "new_password": self.pin}))

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


@mock.patch("account.views.google.verify_google_token")
class TeacherAccountDeleteTest(SchoolClassTestBase):
    """교사가 탈퇴하면 학급과 학생 계정이 함께 사라져야 한다.

    학급을 지우면 소속(ClassMembership)만 CASCADE 로 사라지고 학생 계정은 남는다.
    그 정리까지 되는지 확인한다.
    """
    def setUp(self):
        super().setUp()
        SysOptions.google_client_id = "test-client-id.apps.googleusercontent.com"
        self.teacher.google_sub = "google-sub-teacher"
        self.teacher.save()
        self.class_id = self._create_class().data["data"]["id"]
        self._create_students(self.class_id, 1, 3)
        self.url = self.reverse("delete_account_api")

    def _delete(self, verify):
        verify.return_value = {"sub": "google-sub-teacher", "email": "t@school.kr",
                               "email_verified": True}
        return self.client.post(self.url, data={"credential": "x"})

    def test_preview_shows_what_will_be_removed(self, verify):
        resp = self.client.get(self.url)
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["class_count"], 1)
        self.assertEqual(resp.data["data"]["student_count"], 3)

    def test_classes_and_students_are_removed(self, verify):
        student_ids = list(ClassMembership.objects.values_list("student_id", flat=True))
        self.assertEqual(len(student_ids), 3)

        resp = self._delete(verify)
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["deleted_students"], 3)

        self.assertFalse(SchoolClass.objects.filter(id=self.class_id).exists())
        self.assertFalse(ClassMembership.objects.exists())
        # 고아 계정이 남지 않아야 한다
        self.assertFalse(User.objects.filter(id__in=student_ids).exists())

    def test_other_teacher_class_is_untouched(self, verify):
        # 다른 교사의 학급·학생은 그대로 있어야 한다
        self.client.logout()
        other = self.create_teacher(username="박선생")
        other_class = self._create_class(grade=5, class_no=1).data["data"]["id"]
        self._create_students(other_class, 1, 2)
        self.client.logout()
        self.client.login(username=self.teacher.username, password="teacher")

        # 삭제가 실제로 성공했는지 먼저 확인한다.
        # 실패해도 "다른 교사 학급이 남아 있다" 는 통과해버리기 때문이다.
        self.assertSuccess(self._delete(verify))

        self.assertTrue(SchoolClass.objects.filter(id=other_class).exists())
        self.assertEqual(ClassMembership.objects.filter(school_class_id=other_class).count(), 2)
        self.assertTrue(User.objects.filter(id=other.id).exists())


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
        self.assertNotIn(self.student.username, public_display_name(self.student))

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
            difficulty="L1", source="", created_by=self.teacher)
        Submission.objects.create(problem=problem, user=self.student,
                                  code="print(1)", language="Python3", result=0)

        self.client.logout()
        resp = self.client.get(self.reverse("submission_list_api") + "?limit=10")
        self.assertSuccess(resp)
        rows = resp.data["data"]["results"]
        names = [r["username"] for r in rows]
        self.assertIn("코알라초등학교 학생", names)
        self.assertNotIn(self.student.username, names)
        # 표시 이름으로는 프로필을 찾을 수 없으므로 화면에서 링크를 걸면 안 된다
        self.assertFalse(rows[0]["profile_visible"])

    def test_rank_api_hides_internal_username(self):
        self.client.logout()
        resp = self.client.get(self.reverse("user_rank_api") + "?offset=0&limit=10")
        self.assertSuccess(resp)
        for row in resp.data["data"]["results"]:
            self.assertNotIn(self.student.username, row["user"]["username"])
            self.assertFalse(row["user"]["profile_visible"])

    def test_profile_link_allowed_for_google_user(self):
        learner = self.create_user("코딩왕", "pass123")
        resp = self.client.get(self.reverse("user_profile_api") + "?username=코딩왕")
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["user"]["username"], learner.username)

    def test_student_profile_not_readable_by_others(self):
        """내부 아이디를 알아내도 남의 학생 프로필은 열리지 않는다"""
        self.create_user("코딩왕", "pass123")
        resp = self.client.get(self.reverse("user_profile_api")
                               + f"?username={self.student.username}")
        self.assertFailed(resp, "사용자가 존재하지 않습니다")

    def test_student_can_read_own_profile(self):
        self.student.set_password("1234")
        self.student.save(update_fields=["password"])
        self.client.logout()
        self.client.login(username=self.student.username, password="1234")
        resp = self.client.get(self.reverse("user_profile_api")
                               + f"?username={self.student.username}")
        self.assertSuccess(resp)


class MyStudentsFilterTest(SchoolClassTestBase):
    """교사의 "내 학생만 보기". 다른 교사의 학생은 걸러져야 한다."""
    def setUp(self):
        super().setUp()
        class_id = self._create_class()
        self._create_students(class_id, 1, 1)
        self.student = ClassMembership.objects.get(number=1).student

        # 다른 교사와 그 학생
        self.client.logout()
        self.other_teacher = self.create_teacher(username="박선생")
        other_class = self._create_class(grade=5, class_no=1)
        self._create_students(other_class, 1, 1)
        self.other_student = ClassMembership.objects.get(
            school_class_id=other_class, number=1).student

        from problem.models import Problem
        from submission.models import Submission
        problem = Problem.objects.create(
            _id="P1", title="t", description="d", input_description="i",
            output_description="o", samples=[], test_case_id="x", test_case_score=[],
            hint="", languages=["Python3"], template={}, time_limit=1000,
            memory_limit=256, spj=False, rule_type="ACM", visible=True,
            difficulty="L1", source="", created_by=self.teacher)
        for user in (self.student, self.other_student):
            Submission.objects.create(problem=problem, user=user, code="print(1)",
                                      language="Python3", result=0)
            user.userprofile.accepted_number = 1
            user.userprofile.submission_number = 1
            user.userprofile.save()

    def _create_class(self, grade=3, class_no=2):
        return super()._create_class(grade=grade, class_no=class_no).data["data"]["id"]

    def test_submission_list_filter(self):
        url = self.reverse("submission_list_api") + "?limit=10&my_students=1"
        self.assertEqual(len(self.client.get(url).data["data"]["results"]), 1)

        self.client.logout()
        self.client.login(username="김선생", password="teacher")
        self.assertEqual(len(self.client.get(url).data["data"]["results"]), 1)

    def test_rank_filter(self):
        url = self.reverse("user_rank_api") + "?offset=0&limit=10&my_students=1"
        self.assertEqual(self.client.get(url).data["data"]["total"], 1)
        # 필터를 빼면 둘 다 보인다
        self.assertEqual(self.client.get(
            self.reverse("user_rank_api") + "?offset=0&limit=10").data["data"]["total"], 2)

    def test_non_teacher_flag_is_ignored(self):
        """교사가 아닌 사용자가 넣으면 무시한다(전체 목록이 그대로 나온다)"""
        self.client.logout()
        self.create_user("개인학생", "pass123")
        url = self.reverse("user_rank_api") + "?offset=0&limit=10&my_students=1"
        self.assertEqual(self.client.get(url).data["data"]["total"], 2)


class NeisSyncTest(APITestCase):
    """나이스 응답을 흉내 내어 적재 로직을 검증한다(실제 API 는 호출하지 않는다)."""

    def _body(self, rows, total=None):
        return {
            "schoolInfo": [
                {"head": [{"list_total_count": total if total is not None else len(rows)},
                          {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다."}}]},
                {"row": rows},
            ]
        }

    def _row(self, code, name, kind="초등학교"):
        return {"SD_SCHUL_CODE": code, "SCHUL_NM": name, "SCHUL_KND_SC_NM": kind,
                "ATPT_OFCDC_SC_NM": "전라남도교육청", "ORG_RDNMA": "전남 어딘가"}

    @mock.patch("account.neis.requests.get")
    def test_sync_saves_schools(self, get):
        from .neis import sync_schools
        get.return_value = mock.Mock(status_code=200,
                                     json=lambda: self._body([self._row("A1", "가초등학교"),
                                                              self._row("A2", "나중학교", "중학교")]))
        saved = sync_schools("dummy-key")
        self.assertEqual(saved, 2)
        self.assertEqual(School.objects.count(), 2)
        self.assertEqual(School.objects.get(code="A1").name, "가초등학교")

    @mock.patch("account.neis.requests.get")
    def test_sync_is_idempotent_and_updates(self, get):
        from .neis import sync_schools
        get.return_value = mock.Mock(status_code=200,
                                     json=lambda: self._body([self._row("A1", "옛이름")]))
        sync_schools("dummy-key")
        get.return_value = mock.Mock(status_code=200,
                                     json=lambda: self._body([self._row("A1", "새이름")]))
        sync_schools("dummy-key")
        self.assertEqual(School.objects.count(), 1)
        self.assertEqual(School.objects.get(code="A1").name, "새이름")

    @mock.patch("account.neis.requests.get")
    def test_skips_unwanted_kinds(self, get):
        from .neis import sync_schools
        get.return_value = mock.Mock(status_code=200,
                                     json=lambda: self._body([self._row("A1", "가유치원", "유치원")]))
        self.assertEqual(sync_schools("dummy-key"), 0)
        self.assertEqual(School.objects.count(), 0)

    @mock.patch("account.neis.requests.get")
    def test_skips_blank_school_code(self, get):
        """개교 예정 "(가칭)" 학교는 학교코드가 공백으로 온다.

        걸러내지 않으면 한 배치에 빈 코드가 여러 개 들어가
        ON CONFLICT 가 같은 행을 두 번 갱신하려다 실패한다.
        """
        from .neis import sync_schools
        rows = [self._row("   ", "(가칭)에코1초등학교"),
                self._row("", "(가칭)에코3중학교", "중학교"),
                self._row("A1", "진짜초등학교")]
        get.return_value = mock.Mock(status_code=200, json=lambda: self._body(rows))
        self.assertEqual(sync_schools("dummy-key"), 1)
        self.assertEqual(School.objects.count(), 1)
        self.assertEqual(School.objects.get().code, "A1")

    @mock.patch("account.neis.requests.get")
    def test_deduplicates_within_page(self, get):
        """같은 페이지에 같은 코드가 두 번 와도 실패하지 않는다"""
        from .neis import sync_schools
        rows = [self._row("A1", "먼저"), self._row("A1", "나중")]
        get.return_value = mock.Mock(status_code=200, json=lambda: self._body(rows))
        self.assertEqual(sync_schools("dummy-key"), 1)
        self.assertEqual(School.objects.get(code="A1").name, "나중")

    @mock.patch("account.neis.requests.get")
    def test_api_error_raises(self, get):
        from .neis import NeisError, sync_schools
        get.return_value = mock.Mock(
            status_code=200,
            json=lambda: {"RESULT": {"CODE": "INFO-300", "MESSAGE": "인증키가 유효하지 않습니다."}})
        with self.assertRaises(NeisError):
            sync_schools("bad-key")

    @mock.patch("account.neis.requests.get")
    def test_no_data_is_not_an_error(self, get):
        from .neis import sync_schools
        get.return_value = mock.Mock(
            status_code=200,
            json=lambda: {"RESULT": {"CODE": "INFO-200", "MESSAGE": "해당하는 데이터가 없습니다."}})
        self.assertEqual(sync_schools("dummy-key"), 0)

    def test_missing_key_raises(self):
        from .neis import NeisError, sync_schools
        with self.assertRaises(NeisError):
            sync_schools("")

    def test_sync_api_requires_super_admin(self):
        self.create_teacher()
        self.assertFailed(self.client.post(self.reverse("school_sync_api"), data={}))

    def test_stale_running_can_be_restarted(self):
        """워커가 죽어 running 인 채 멈춘 작업은 다시 시작할 수 있어야 한다"""
        from datetime import timedelta
        from django.utils.timezone import now
        from .neis import is_running
        SysOptions.school_sync_status = {
            "state": "running",
            "updated_at": (now() - timedelta(minutes=30)).isoformat(),
        }
        self.assertFalse(is_running())

        SysOptions.school_sync_status = {
            "state": "running", "updated_at": now().isoformat(),
        }
        self.assertTrue(is_running())
        SysOptions.school_sync_status = {}

    def test_sync_api_requires_key(self):
        self.create_super_admin()
        SysOptions.neis_api_key = ""
        self.assertFailed(self.client.post(self.reverse("school_sync_api"), data={}),
                          "먼저 나이스 API 키를 저장하세요")
