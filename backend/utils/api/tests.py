from django.urls import reverse
from django.test.testcases import TestCase
from rest_framework.test import APIClient

from account.models import AdminType, ProblemPermission, User, UserProfile


class APITestCase(TestCase):
    client_class = APIClient

    def create_user(self, username, password, admin_type=AdminType.REGULAR_USER, login=True,
                    problem_permission=ProblemPermission.NONE):
        user = User.objects.create(username=username, admin_type=admin_type, problem_permission=problem_permission)
        user.set_password(password)
        UserProfile.objects.create(user=user)
        user.save()
        if login:
            self.client.login(username=username, password=password)
        return user

    def create_teacher(self, username="teacher", password="teacher", login=True):
        return self.create_user(username=username, password=password, login=login,
                                admin_type=AdminType.TEACHER,
                                problem_permission=ProblemPermission.OWN)

    def create_admin(self, username="admin", password="admin", login=True, **permissions):
        """관리자. 대회 권한은 기본으로 켠다(예전 관리자는 누구나 대회를 열 수 있었다).
        permissions 로 teacher_permission·contest_permission·avatar_permission 을 바꾼다."""
        user = self.create_user(username=username, password=password, admin_type=AdminType.ADMIN,
                                problem_permission=ProblemPermission.OWN,
                                login=login)
        for k, v in {"contest_permission": True, **permissions}.items():
            setattr(user, k, v)
        user.save()
        return user

    def create_super_admin(self, username="root", password="root", login=True):
        return self.create_user(username=username, password=password, admin_type=AdminType.SUPER_ADMIN,
                                problem_permission=ProblemPermission.ALL, login=login)

    def reverse(self, url_name, *args, **kwargs):
        return reverse(url_name, *args, **kwargs)

    def assertSuccess(self, response):
        if not response.data["error"] is None:
            raise AssertionError("response with errors, response: " + str(response.data))

    def assertFailed(self, response, msg=None):
        self.assertTrue(response.data["error"] is not None)
        if msg:
            self.assertEqual(response.data["data"], msg)
