import time

from unittest import mock
from datetime import timedelta
from copy import deepcopy

from django.contrib import auth
from django.utils.timezone import now

from utils.api.tests import APITestCase
from utils.shortcuts import rand_str
from options.options import SysOptions

from .models import AdminType, ProblemPermission, TeacherApplication, User
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


class DuplicateUserCheckAPITest(APITestCase):
    def setUp(self):
        user = self.create_user("test", "test123", login=False)
        user.email = "test@test.com"
        user.save()
        self.url = self.reverse("check_username_or_email")

    def test_duplicate_username(self):
        resp = self.client.post(self.url, data={"username": "test"})
        data = resp.data["data"]
        self.assertEqual(data["username"], True)
        resp = self.client.post(self.url, data={"username": "Test"})
        self.assertEqual(resp.data["data"]["username"], True)

    def test_ok_username(self):
        resp = self.client.post(self.url, data={"username": "test1"})
        data = resp.data["data"]
        self.assertFalse(data["username"])

    def test_duplicate_email(self):
        resp = self.client.post(self.url, data={"email": "test@test.com"})
        self.assertEqual(resp.data["data"]["email"], True)
        resp = self.client.post(self.url, data={"email": "Test@Test.com"})
        self.assertTrue(resp.data["data"]["email"])

    def test_ok_email(self):
        resp = self.client.post(self.url, data={"email": "aa@test.com"})
        self.assertFalse(resp.data["data"]["email"])


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


class CaptchaTest(APITestCase):
    def _set_captcha(self, session):
        captcha = rand_str(4)
        session["_django_captcha_key"] = captcha
        session["_django_captcha_expires_time"] = int(time.time()) + 30
        session.save()
        return captcha


class UserRegisterAPITest(APITestCase):
    """옛 회원가입 경로는 닫혀 있어야 한다. 가입은 구글로만 받는다."""
    def setUp(self):
        self.register_url = self.reverse("user_register_api")

    def test_register_is_closed(self):
        resp = self.client.post(self.register_url, data={
            "username": "test_user", "password": "testuserpassword",
            "email": "test@qduoj.com", "captcha": "1234"})
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
        update_data = {"real_name": "zemal", "submission_number": 233}
        resp = self.client.put(self.url, data=update_data)
        self.assertSuccess(resp)
        data = resp.data["data"]
        self.assertEqual(data["real_name"], "zemal")
        self.assertEqual(data["submission_number"], 0)


@mock.patch("account.views.oj.send_email_async.send")
class ApplyResetPasswordAPITest(CaptchaTest):
    def setUp(self):
        self.create_user("test", "test123", login=False)
        user = User.objects.first()
        user.email = "test@oj.com"
        user.save()
        self.url = self.reverse("apply_reset_password_api")
        self.data = {"email": "test@oj.com", "captcha": self._set_captcha(self.client.session)}

    def _refresh_captcha(self):
        self.data["captcha"] = self._set_captcha(self.client.session)

    def test_apply_reset_password(self, send_email_send):
        resp = self.client.post(self.url, data=self.data)
        self.assertSuccess(resp)
        send_email_send.assert_called()

    def test_apply_reset_password_twice_in_20_mins(self, send_email_send):
        self.test_apply_reset_password()
        send_email_send.reset_mock()
        self._refresh_captcha()
        resp = self.client.post(self.url, data=self.data)
        self.assertDictEqual(resp.data, {"error": "error", "data": "비밀번호 재설정은 20분에 한 번만 요청할 수 있습니다"})
        send_email_send.assert_not_called()

    def test_apply_reset_password_again_after_20_mins(self, send_email_send):
        self.test_apply_reset_password()
        user = User.objects.first()
        user.reset_password_token_expire_time = now() - timedelta(minutes=21)
        user.save()
        self._refresh_captcha()
        self.test_apply_reset_password()


    def test_google_account_blocked(self, send_email_send):
        user = User.objects.first()
        user.google_sub = "google-sub-1"
        user.save()
        resp = self.client.post(self.url, data={"email": "test@oj.com",
                                                "captcha": self._set_captcha(self.client.session)})
        self.assertFailed(resp, "구글 계정으로 가입하셨습니다. 구글로 로그인해주세요")

    def test_student_account_blocked(self, send_email_send):
        teacher = self.create_teacher(login=False)
        user = User.objects.get(username="test")
        user.created_by = teacher
        user.save()
        resp = self.client.post(self.url, data={"email": "test@oj.com",
                                                "captcha": self._set_captcha(self.client.session)})
        self.assertFailed(resp, "학교에서 발급받은 계정입니다. 선생님께 문의하세요")


class ResetPasswordAPITest(CaptchaTest):
    def setUp(self):
        self.create_user("test", "test123", login=False)
        self.url = self.reverse("reset_password_api")
        user = User.objects.first()
        user.reset_password_token = "online_judge?"
        user.reset_password_token_expire_time = now() + timedelta(minutes=20)
        user.save()
        self.data = {"token": user.reset_password_token,
                     "captcha": self._set_captcha(self.client.session),
                     "password": "test456"}

    def test_reset_password_with_correct_token(self):
        resp = self.client.post(self.url, data=self.data)
        self.assertSuccess(resp)
        self.assertTrue(self.client.login(username="test", password="test456"))

    def test_reset_password_with_invalid_token(self):
        self.data["token"] = "aaaaaaaaaaa"
        resp = self.client.post(self.url, data=self.data)
        self.assertDictEqual(resp.data, {"error": "error", "data": "토큰이 존재하지 않습니다"})

    def test_reset_password_with_expired_token(self):
        user = User.objects.first()
        user.reset_password_token_expire_time = now() - timedelta(seconds=30)
        user.save()
        resp = self.client.post(self.url, data=self.data)
        self.assertDictEqual(resp.data, {"error": "error", "data": "토큰이 만료되었습니다"})


class UserChangeEmailAPITest(APITestCase):
    def setUp(self):
        self.url = self.reverse("user_change_email_api")
        self.user = self.create_user("test", "test123")
        self.new_mail = "test@oj.com"
        self.data = {"password": "test123", "new_email": self.new_mail}

    def test_change_email_success(self):
        resp = self.client.post(self.url, data=self.data)
        self.assertSuccess(resp)

    def test_wrong_password(self):
        self.data["password"] = "aaaa"
        resp = self.client.post(self.url, data=self.data)
        self.assertDictEqual(resp.data, {"error": "error", "data": "비밀번호가 올바르지 않습니다"})

    def test_duplicate_email(self):
        u = self.create_user("aa", "bb", login=False)
        u.email = self.new_mail
        u.save()
        resp = self.client.post(self.url, data=self.data)
        self.assertDictEqual(resp.data, {"error": "error", "data": "다른 계정이 사용 중인 이메일입니다"})


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


class ProfileProblemDisplayIDRefreshAPITest(APITestCase):
    def setUp(self):
        pass


class AdminUserTest(APITestCase):
    def setUp(self):
        self.user = self.create_super_admin(login=True)
        self.username = self.password = "test"
        self.regular_user = self.create_user(username=self.username, password=self.password, login=False)
        self.url = self.reverse("user_admin_api")
        self.data = {"id": self.regular_user.id, "username": self.username, "real_name": "test_name",
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
        data = {"users": [["user1", "pass1", "eami1@e.com", "user1"],
                          ["user2", "pass3", "eamil3@e.com", "user2"]]
                }
        resp = self.client.post(self.url, data)
        self.assertSuccess(resp)
        self.assertEqual(User.objects.all().count(), 4)

    def test_import_duplicate_user(self):
        data = {"users": [["user1", "pass1", "eami1@e.com", "user1"],
                          ["user1", "pass1", "eami1@e.com", "user1"]]
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

    def test_student_username_pattern_reserved(self, verify):
        """학생 계정 아이디 형태(c12-01)는 닉네임으로 선점할 수 없다"""
        verify.return_value = self._claims()
        self.client.post(self.url, data={"credential": "x"})
        resp = self.client.post(self.url, data={"credential": "x", "nickname": "c12-01"})
        self.assertFailed(resp, "사용할 수 없는 닉네임입니다")

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
