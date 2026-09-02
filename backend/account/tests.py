from unittest import mock
from copy import deepcopy

from django.contrib import auth

from utils.api.tests import APITestCase
from options.options import SysOptions

from .models import (AdminType, ProblemPermission, TeacherApplication,
                     TeacherApplicationStatus, User, UserProfile)
from utils.constants import ContestRuleType


class PermissionDecoratorTest(APITestCase):
    def setUp(self):
        self.regular_user = User.objects.create(username="regular_user")
        self.admin = User.objects.create(username="admin")
        self.super_admin = User.objects.create(username="super_admin")
        self.request = mock.MagicMock()
        self.request.user.is_authenticated = mock.MagicMock()

    def test_login_required(self):
        self.request.user.is_authenticated.return_value = False

    def test_admin_required(self):
        pass

    def test_super_admin_required(self):
        pass


class UserLoginAPITest(APITestCase):
    def setUp(self):
        self.username = self.password = "test"
        self.user = self.create_user(username=self.username, password=self.password, login=False)
        self.login_url = self.reverse("user_login_api")

    def test_login_with_correct_info(self):
        response = self.client.post(self.login_url,
                                    data={"username": self.username, "password": self.password})
        self.assertDictEqual(response.data, {"error": None, "data": "Succeeded"})

        user = auth.get_user(self.client)
        self.assertTrue(user.is_authenticated)

    def test_login_with_correct_info_upper_username(self):
        resp = self.client.post(self.login_url, data={"username": self.username.upper(), "password": self.password})
        self.assertDictEqual(resp.data, {"error": None, "data": "Succeeded"})
        user = auth.get_user(self.client)
        self.assertTrue(user.is_authenticated)

    def test_login_with_wrong_info(self):
        response = self.client.post(self.login_url,
                                    data={"username": self.username, "password": "invalid_password"})
        self.assertDictEqual(response.data, {"error": "error", "data": "사용자명 또는 비밀번호가 올바르지 않습니다"})

        user = auth.get_user(self.client)
        self.assertFalse(user.is_authenticated)

    def test_user_disabled(self):
        self.user.is_disabled = True
        self.user.save()
        resp = self.client.post(self.login_url, data={"username": self.username,
                                                      "password": self.password})
        self.assertDictEqual(resp.data, {"error": "error", "data": "비활성화된 계정입니다"})


class UserRegisterAPITest(APITestCase):
    """옛 회원가입 경로는 닫혀 있어야 한다. 가입은 구글로만 받는다."""
    def setUp(self):
        self.register_url = self.reverse("user_register_api")

    def test_register_is_closed(self):
        resp = self.client.post(self.register_url, data={
            "username": "test_user", "password": "testuserpassword",
            "email": "test@qduoj.com"})
        self.assertFailed(resp, "구글 계정으로 가입해주세요")
        self.assertFalse(User.objects.filter(username="test_user").exists())


class SessionManagementAPITest(APITestCase):
    def setUp(self):
        self.create_user("test", "test123")
        self.url = self.reverse("session_management_api")
        login_url = self.reverse("user_login_api")
        self.client.post(login_url, data={"username": "test", "password": "test123"})

    def test_get_sessions(self):
        resp = self.client.get(self.url)
        self.assertSuccess(resp)
        data = resp.data["data"]
        self.assertEqual(len(data), 1)

    def test_delete_session_with_invalid_key(self):
        resp = self.client.delete(self.url + "?session_key=aaaaaaaaaa")
        self.assertDictEqual(resp.data, {"error": "error", "data": "session_key가 올바르지 않습니다"})


class SessionListRobustnessTest(APITestCase):
    """세션에 ip 등이 아직 저장되지 않아도 목록 조회가 실패하면 안 된다.

    미들웨어는 응답 시점에 세션을 저장하므로, 로그인 직후 첫 요청에서는
    저장소 사본에 ip 가 없을 수 있다(원본 qduoj 는 여기서 KeyError 로 죽었다).
    """
    def test_session_without_ip(self):
        user = self.create_user("test", "test123")
        resp = self.client.get(self.reverse("session_management_api"))
        self.assertSuccess(resp)

        # 저장소에 ip 가 없는 세션 키를 억지로 끼워 넣어도 살아남아야 한다
        from django.contrib.sessions.backends.cache import SessionStore
        orphan = SessionStore()
        orphan["_auth_user_id"] = str(user.id)
        orphan.save()
        user.session_keys.append(orphan.session_key)
        user.save()

        resp = self.client.get(self.reverse("session_management_api"))
        self.assertSuccess(resp)
        self.assertTrue(any(s["session_key"] == orphan.session_key
                            for s in resp.data["data"]))


class UserProfileAPITest(APITestCase):
    def setUp(self):
        self.url = self.reverse("user_profile_api")

    def test_get_profile_without_login(self):
        resp = self.client.get(self.url)
        self.assertDictEqual(resp.data, {"error": None, "data": None})

    def test_get_profile(self):
        self.create_user("test", "test123")
        resp = self.client.get(self.url)
        self.assertSuccess(resp)

    def test_update_profile(self):
        self.create_user("test", "test123")
        # submission_number 는 집계값이라 수정 요청에 실려도 반영되지 않아야 한다
        resp = self.client.put(self.url, data={"avatar": "/x.png", "submission_number": 233})
        self.assertSuccess(resp)
        data = resp.data["data"]
        self.assertEqual(data["avatar"], "/x.png")
        self.assertEqual(data["submission_number"], 0)

    def test_own_profile_keeps_email(self):
        user = self.create_user("test", "test123")
        user.email = "me@test.com"
        user.save()
        resp = self.client.get(self.url)
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["user"]["email"], "me@test.com")

    def test_other_profile_exposes_only_public_fields(self):
        """남의 프로필에는 아이디와 풀이 통계만 실린다.

        created_by 가 나가면 학생들을 담당 교사 단위로 묶어볼 수 있고,
        email 이 나가면 아이디만 알면 주소를 긁어갈 수 있다.
        """
        other = self.create_user("other", "test123", login=False)
        other.email = "other@test.com"
        other.save()
        self.create_user("me", "test123")

        resp = self.client.get(self.url + "?username=other")
        self.assertSuccess(resp)
        data = resp.data["data"]
        self.assertEqual(set(data["user"]), {"id", "username"})
        self.assertEqual(set(data),
                         {"user", "avatar", "accepted_number", "submission_number",
                          "total_score", "acm_problems_status", "oi_problems_status"})


class UserChangePasswordAPITest(APITestCase):
    def setUp(self):
        self.url = self.reverse("user_change_password_api")

        self.username = "test_user"
        self.old_password = "testuserpassword"
        self.new_password = "new_password"
        self.user = self.create_user(username=self.username, password=self.old_password, login=False)

        self.data = {"old_password": self.old_password, "new_password": self.new_password}

    def test_login_required(self):
        response = self.client.post(self.url, data=self.data)
        self.assertEqual(response.data, {"error": "permission-denied", "data": "먼저 로그인하세요"})

    def test_valid_ola_password(self):
        self.assertTrue(self.client.login(username=self.username, password=self.old_password))
        response = self.client.post(self.url, data=self.data)
        self.assertEqual(response.data, {"error": None, "data": "Succeeded"})
        self.assertTrue(self.client.login(username=self.username, password=self.new_password))

    def test_invalid_old_password(self):
        self.assertTrue(self.client.login(username=self.username, password=self.old_password))
        self.data["old_password"] = "invalid"
        response = self.client.post(self.url, data=self.data)
        self.assertEqual(response.data, {"error": "error", "data": "기존 비밀번호가 올바르지 않습니다"})


class UserRankAPITest(APITestCase):
    def setUp(self):
        self.url = self.reverse("user_rank_api")
        self.create_user("test1", "test123", login=False)
        self.create_user("test2", "test123", login=False)
        test1 = User.objects.get(username="test1")
        profile1 = test1.userprofile
        profile1.submission_number = 10
        profile1.accepted_number = 10
        profile1.total_score = 240
        profile1.save()

        test2 = User.objects.get(username="test2")
        profile2 = test2.userprofile
        profile2.submission_number = 15
        profile2.accepted_number = 10
        profile2.total_score = 700
        profile2.save()

    def test_teacher_is_included(self):
        """교사도 학생과 함께 문제를 푸는 사용자라 순위에 나와야 한다.

        상위 OJ 에는 교사 유형이 없어 "일반 사용자"만 담았고, 교사를 추가한 뒤로
        교사가 아무리 풀어도 순위에 나오지 않았다.
        """
        teacher = self.create_teacher(username="코딩선생", login=False)
        profile = teacher.userprofile
        profile.submission_number = 5
        profile.accepted_number = 5
        profile.total_score = 100
        profile.save()

        resp = self.client.get(self.url, data={"rule": ContestRuleType.ACM})
        self.assertSuccess(resp)
        names = [row["user"]["username"] for row in resp.data["data"]["results"]]
        self.assertIn("코딩선생", names)

    def test_admin_is_excluded(self):
        """관리자는 운영자라 순위에 넣지 않는다."""
        admin = self.create_super_admin(username="root", login=False)
        profile = admin.userprofile
        profile.submission_number = 99
        profile.accepted_number = 99
        profile.save()

        resp = self.client.get(self.url, data={"rule": ContestRuleType.ACM})
        self.assertSuccess(resp)
        names = [row["user"]["username"] for row in resp.data["data"]["results"]]
        self.assertNotIn("root", names)

    def test_get_acm_rank(self):
        resp = self.client.get(self.url, data={"rule": ContestRuleType.ACM})
        self.assertSuccess(resp)
        data = resp.data["data"]["results"]
        self.assertEqual(data[0]["user"]["username"], "test1")
        self.assertEqual(data[1]["user"]["username"], "test2")

    def test_get_oi_rank(self):
        resp = self.client.get(self.url, data={"rule": ContestRuleType.OI})
        self.assertSuccess(resp)
        data = resp.data["data"]["results"]
        self.assertEqual(data[0]["user"]["username"], "test2")
        self.assertEqual(data[1]["user"]["username"], "test1")

    def test_admin_role_filted(self):
        self.create_admin("admin", "admin123")
        admin = User.objects.get(username="admin")
        profile1 = admin.userprofile
        profile1.submission_number = 20
        profile1.accepted_number = 5
        profile1.total_score = 300
        profile1.save()
        resp = self.client.get(self.url, data={"rule": ContestRuleType.ACM})
        self.assertSuccess(resp)
        self.assertEqual(len(resp.data["data"]), 2)

        resp = self.client.get(self.url, data={"rule": ContestRuleType.OI})
        self.assertSuccess(resp)
        self.assertEqual(len(resp.data["data"]), 2)


class AdminUserTest(APITestCase):
    def setUp(self):
        self.user = self.create_super_admin(login=True)
        self.username = self.password = "test"
        self.regular_user = self.create_user(username=self.username, password=self.password, login=False)
        self.url = self.reverse("user_admin_api")
        self.data = {"id": self.regular_user.id, "username": self.username,
                     "email": "test@qq.com", "admin_type": AdminType.REGULAR_USER,
                     "problem_permission": ProblemPermission.OWN, "is_disabled": False}

    def test_user_list(self):
        response = self.client.get(self.url)
        self.assertSuccess(response)

    def test_edit_user_successfully(self):
        response = self.client.put(self.url, data=self.data)
        self.assertSuccess(response)
        resp_data = response.data["data"]
        self.assertEqual(resp_data["username"], self.username)
        self.assertEqual(resp_data["email"], "test@qq.com")
        self.assertEqual(resp_data["is_disabled"], False)
        self.assertEqual(resp_data["problem_permission"], ProblemPermission.NONE)

        self.assertTrue(self.regular_user.check_password("test"))

    def test_edit_user_password(self):
        data = self.data
        new_password = "testpassword"
        data["password"] = new_password
        response = self.client.put(self.url, data=data)
        self.assertSuccess(response)
        user = User.objects.get(id=self.regular_user.id)
        self.assertFalse(user.check_password(self.password))
        self.assertTrue(user.check_password(new_password))

    def test_import_users(self):
        data = {"users": [["user1", "pass1", "eami1@e.com"],
                          ["user2", "pass3", "eamil3@e.com"]]
                }
        resp = self.client.post(self.url, data)
        self.assertSuccess(resp)
        self.assertEqual(User.objects.all().count(), 4)

    def test_import_duplicate_user(self):
        data = {"users": [["user1", "pass1", "eami1@e.com"],
                          ["user1", "pass1", "eami1@e.com"]]
                }
        resp = self.client.post(self.url, data)
        self.assertFailed(resp, "이미 사용 중인 사용자명이 있습니다")
        self.assertEqual(User.objects.all().count(), 2)

    def test_delete_users(self):
        self.test_import_users()
        user_ids = User.objects.filter(username__in=["user1", "user2"]).values_list("id", flat=True)
        user_ids = ",".join([str(id) for id in user_ids])
        resp = self.client.delete(self.url + "?id=" + user_ids)
        self.assertSuccess(resp)
        self.assertEqual(User.objects.all().count(), 2)


class GenerateUserAPITest(APITestCase):
    def setUp(self):
        self.create_super_admin()
        self.url = self.reverse("generate_user_api")
        self.data = {
            "number_from": 100, "number_to": 105,
            "prefix": "pre", "suffix": "suf",
            "default_email": "test@test.com",
            "password_length": 8
        }

    def test_error_case(self):
        data = deepcopy(self.data)
        data["prefix"] = "t" * 16
        data["suffix"] = "s" * 14
        resp = self.client.post(self.url, data=data)
        self.assertEqual(resp.data["data"], "사용자명은 32자를 넘을 수 없습니다")

        data2 = deepcopy(self.data)
        data2["number_from"] = 106
        resp = self.client.post(self.url, data=data2)
        self.assertEqual(resp.data["data"], "시작 번호는 끝 번호보다 작아야 합니다")

    @mock.patch("account.views.admin.xlsxwriter.Workbook")
    def test_generate_user_success(self, mock_workbook):
        resp = self.client.post(self.url, data=self.data)
        self.assertSuccess(resp)
        mock_workbook.assert_called()


@mock.patch("account.views.google.verify_google_token")
class GoogleLoginAPITest(APITestCase):
    def setUp(self):
        self.url = self.reverse("google_login_api")
        SysOptions.google_client_id = "test-client-id.apps.googleusercontent.com"
        SysOptions.allow_register = True

    def _claims(self, **kwargs):
        data = {"sub": "google-sub-1", "email": "teacher@school.kr",
                "email_verified": True, "name": "김교사"}
        data.update(kwargs)
        return data

    def _signup(self, verify, nickname="코딩선생", **claims):
        verify.return_value = self._claims(**claims)
        self.client.post(self.url, data={"credential": "x"})          # nickname_required
        return self.client.post(self.url, data={"credential": "x", "nickname": nickname})

    def test_client_id_not_configured(self, verify):
        SysOptions.google_client_id = ""
        self.assertFailed(self.client.post(self.url, data={"credential": "x"}))
        verify.assert_not_called()

    def test_invalid_token(self, verify):
        verify.return_value = None
        self.assertFailed(self.client.post(self.url, data={"credential": "bad"}),
                          "구글 인증에 실패했습니다. 다시 시도해주세요")

    def test_email_not_verified(self, verify):
        verify.return_value = self._claims(email_verified=False)
        self.assertFailed(self.client.post(self.url, data={"credential": "x"}))

    def test_first_login_asks_for_nickname(self, verify):
        verify.return_value = self._claims()
        resp = self.client.post(self.url, data={"credential": "x"})
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["status"], "nickname_required")
        # 아직 계정을 만들지 않는다
        self.assertFalse(User.objects.filter(google_sub="google-sub-1").exists())

    def test_signup_logs_in_as_regular_user(self, verify):
        resp = self._signup(verify)
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["status"], "logged_in")

        user = User.objects.get(google_sub="google-sub-1")
        self.assertEqual(user.username, "코딩선생")
        self.assertEqual(user.admin_type, AdminType.REGULAR_USER)
        # 교사 신청은 자동으로 만들어지지 않는다
        self.assertFalse(TeacherApplication.objects.filter(user=user).exists())
        self.assertTrue(auth.get_user(self.client).is_authenticated)

    def test_duplicate_nickname_rejected(self, verify):
        self.create_user("코딩선생", "pass123", login=False)
        verify.return_value = self._claims()
        self.client.post(self.url, data={"credential": "x"})
        resp = self.client.post(self.url, data={"credential": "x", "nickname": "코딩선생"})
        self.assertFailed(resp, "이미 사용 중인 닉네임입니다")

    def test_student_username_prefix_reserved(self, verify):
        """"학생"으로 시작하는 닉네임은 수업용 계정과 헷갈려 막는다"""
        verify.return_value = self._claims()
        self.client.post(self.url, data={"credential": "x"})
        for nickname in ("학생12345678", "학생회장"):
            resp = self.client.post(self.url, data={"credential": "x", "nickname": nickname})
            self.assertFailed(resp, "학생 계정 구분을 위해 \'학생\'으로 시작할 수 없습니다")

    def test_reapply_after_demotion(self, verify):
        """승인받았다가 관리자가 유형을 되돌리면 다시 신청할 수 있어야 한다.

        TeacherApplication.user 가 OneToOne 이라 새로 만들면 500 이 났다.
        """
        self._signup(verify, nickname="코딩선생")
        user = User.objects.get(username="코딩선생")
        TeacherApplication.objects.create(user=user,
                                          status=TeacherApplicationStatus.APPROVED)

        resp = self.client.post(self.reverse("teacher_application_api"), data={})
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["status"], TeacherApplicationStatus.PENDING)
        self.assertEqual(TeacherApplication.objects.filter(user=user).count(), 1)

    def test_invalid_nickname_rejected(self, verify):
        verify.return_value = self._claims()
        self.client.post(self.url, data={"credential": "x"})
        resp = self.client.post(self.url, data={"credential": "x", "nickname": "a"})
        self.assertFailed(resp)

    def test_second_login_does_not_ask_nickname(self, verify):
        self._signup(verify)
        self.client.logout()
        verify.return_value = self._claims()
        resp = self.client.post(self.url, data={"credential": "x"})
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["status"], "logged_in")
        self.assertEqual(User.objects.filter(google_sub="google-sub-1").count(), 1)

    def test_signup_blocked_when_register_closed(self, verify):
        SysOptions.allow_register = False
        verify.return_value = self._claims()
        self.assertFailed(self.client.post(self.url, data={"credential": "x"}))

    def test_existing_user_can_login_when_register_closed(self, verify):
        self._signup(verify)
        self.client.logout()
        SysOptions.allow_register = False
        verify.return_value = self._claims()
        self.assertSuccess(self.client.post(self.url, data={"credential": "x"}))

    def test_links_existing_account_by_email(self, verify):
        existing = self.create_user("existing", "pass123", login=False)
        existing.email = "teacher@school.kr"
        existing.save()

        verify.return_value = self._claims()
        resp = self.client.post(self.url, data={"credential": "x"})
        self.assertSuccess(resp)
        existing.refresh_from_db()
        self.assertEqual(existing.google_sub, "google-sub-1")

    def test_student_account_cannot_use_google(self, verify):
        teacher = self.create_teacher(login=False)
        student = self.create_user("kim3-01", "1234", login=False)
        student.email = "teacher@school.kr"
        student.created_by = teacher
        student.save()

        verify.return_value = self._claims()
        resp = self.client.post(self.url, data={"credential": "x"})
        self.assertFailed(resp, "학교에서 발급받은 계정입니다. 선생님께 문의하세요")

    def test_disabled_user_rejected(self, verify):
        self._signup(verify)
        self.client.logout()
        user = User.objects.get(google_sub="google-sub-1")
        user.is_disabled = True
        user.save()

        verify.return_value = self._claims()
        self.assertFailed(self.client.post(self.url, data={"credential": "x"}),
                          "비활성화된 계정입니다")


@mock.patch("account.views.google.verify_google_token")
class AccountDeleteAPITest(APITestCase):
    """회원 탈퇴. 되돌릴 수 없는 동작이라 누가 무엇까지 지울 수 있는지를 고정한다."""
    def setUp(self):
        self.url = self.reverse("delete_account_api")
        SysOptions.google_client_id = "test-client-id.apps.googleusercontent.com"
        self.user = self.create_user("구글선생", "test123")
        self.user.google_sub = "google-sub-1"
        self.user.save()

    def _delete(self, verify, sub="google-sub-1"):
        verify.return_value = {"sub": sub, "email": "t@school.kr", "email_verified": True}
        return self.client.post(self.url, data={"credential": "x"})

    def test_profile_marks_google_account(self, verify):
        # 화면이 이 값으로 탈퇴 버튼을 보여줄지 정한다
        resp = self.client.get(self.reverse("user_profile_api"))
        self.assertTrue(resp.data["data"]["user"]["is_google_account"])

    def test_google_user_can_delete_own_account(self, verify):
        user_id = self.user.id
        self.assertSuccess(self._delete(verify))
        self.assertFalse(User.objects.filter(id=user_id).exists())
        # 프로필도 함께 사라진다
        self.assertFalse(UserProfile.objects.filter(user_id=user_id).exists())

    def test_logged_out_after_delete(self, verify):
        self._delete(verify)
        # 세션이 끊겨 프로필 조회가 빈 응답이 된다
        resp = self.client.get(self.reverse("user_profile_api"))
        self.assertIsNone(resp.data["data"])

    def test_other_google_account_cannot_delete(self, verify):
        self.assertFailed(self._delete(verify, sub="google-sub-other"),
                          "지금 로그인한 계정과 다른 구글 계정입니다")
        self.assertTrue(User.objects.filter(id=self.user.id).exists())

    def test_invalid_credential(self, verify):
        verify.return_value = None
        self.assertFailed(self.client.post(self.url, data={"credential": "x"}),
                          "구글 인증에 실패했습니다. 다시 시도해주세요")
        self.assertTrue(User.objects.filter(id=self.user.id).exists())

    def test_admin_cannot_delete_itself(self, verify):
        # 관리자가 만든 문제·대회·공지가 함께 지워지므로 막는다
        self.client.logout()
        admin = self.create_super_admin("root2", "test123")
        admin.google_sub = "google-sub-admin"
        admin.save()
        self.assertFailed(self.client.post(self.url, data={"credential": "x"}),
                          "관리자 계정은 이 화면에서 탈퇴할 수 없습니다")
        verify.assert_not_called()
        self.assertTrue(User.objects.filter(id=admin.id).exists())

    def test_password_account_cannot_delete(self, verify):
        # 구글로 가입하지 않은 계정(교사가 만든 학생 등)은 대상이 아니다
        self.client.logout()
        self.create_user("일반계정", "test123")
        self.assertFailed(self.client.post(self.url, data={"credential": "x"}),
                          "구글로 가입한 계정만 탈퇴할 수 있습니다. 선생님이나 관리자에게 문의하세요")
        verify.assert_not_called()

    def test_anonymous_rejected(self, verify):
        self.client.logout()
        self.assertFailed(self.client.post(self.url, data={"credential": "x"}))


class TeacherApplyAPITest(APITestCase):
    def setUp(self):
        self.url = self.reverse("teacher_application_api")

    def test_login_required(self):
        self.assertFailed(self.client.post(self.url, data={}))

    def test_apply(self):
        user = self.create_user("개인학습자", "pass123")
        resp = self.client.post(self.url, data={})
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["status"], "pending")
        self.assertTrue(TeacherApplication.objects.filter(user=user).exists())

    def test_cannot_apply_twice(self):
        self.create_user("개인학습자", "pass123")
        self.client.post(self.url, data={})
        self.assertFailed(self.client.post(self.url, data={}), "이미 신청하셨습니다. 승인을 기다려주세요")

    def test_teacher_cannot_apply(self):
        self.create_teacher()
        self.assertFailed(self.client.post(self.url, data={}), "이미 교사 권한이 있습니다")

    def test_student_cannot_apply(self):
        teacher = self.create_teacher(login=False)
        student = self.create_user("kim3-01", "1234")
        student.created_by = teacher
        student.save()
        self.assertFailed(self.client.post(self.url, data={}),
                          "학교에서 발급받은 계정은 교사 신청을 할 수 없습니다")


class TeacherApplicationAdminAPITest(APITestCase):
    def setUp(self):
        self.applicant = self.create_user("applicant", "pass123", login=False)
        self.application = TeacherApplication.objects.create(user=self.applicant)
        self.url = self.reverse("teacher_application_admin_api")

    def test_regular_user_denied(self):
        self.create_user("someone", "pass123")
        self.assertFailed(self.client.get(self.url))

    def test_approve(self):
        self.create_super_admin()
        resp = self.client.put(self.url, data={"id": self.application.id, "status": "approved"})
        self.assertSuccess(resp)

        self.applicant.refresh_from_db()
        self.assertEqual(self.applicant.admin_type, AdminType.TEACHER)
        self.assertEqual(self.applicant.problem_permission, ProblemPermission.OWN)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "approved")
        self.assertIsNotNone(self.application.reviewed_at)

    def test_reject_does_not_grant_permission(self):
        self.create_super_admin()
        resp = self.client.put(self.url, data={"id": self.application.id, "status": "rejected"})
        self.assertSuccess(resp)
        self.applicant.refresh_from_db()
        self.assertEqual(self.applicant.admin_type, AdminType.REGULAR_USER)

    def test_cannot_review_twice(self):
        self.create_super_admin()
        self.client.put(self.url, data={"id": self.application.id, "status": "approved"})
        resp = self.client.put(self.url, data={"id": self.application.id, "status": "rejected"})
        self.assertFailed(resp, "이미 처리된 신청입니다")

    def test_list_filtered_by_status(self):
        self.create_super_admin()
        resp = self.client.get(self.url + "?paging=true&offset=0&limit=10&status=pending")
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["total"], 1)


class TeacherRoleTest(APITestCase):
    def test_teacher_is_not_admin_role(self):
        """교사가 /api/admin/* 전체를 통과하면 안 된다"""
        teacher = self.create_teacher()
        self.assertFalse(teacher.is_admin_role())
        self.assertTrue(teacher.is_teacher())
        # 최고관리자 전용 API 접근 차단 확인
        self.assertFailed(self.client.get(self.reverse("user_admin_api")))
