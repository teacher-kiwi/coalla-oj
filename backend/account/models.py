from django.contrib.auth.models import AbstractBaseUser
from django.conf import settings
from django.db import models
from utils.models import JSONField


class AdminType(object):
    REGULAR_USER = "Regular User"
    TEACHER = "Teacher"
    ADMIN = "Admin"
    SUPER_ADMIN = "Super Admin"


class TeacherApplicationStatus(object):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ProblemPermission(object):
    NONE = "None"
    OWN = "Own"
    ALL = "All"


class UserManager(models.Manager):
    use_in_migrations = True

    def get_by_natural_key(self, username):
        return self.get(**{f"{self.model.USERNAME_FIELD}__iexact": username})


class User(AbstractBaseUser):
    username = models.TextField(unique=True)
    email = models.TextField(null=True)
    create_time = models.DateTimeField(auto_now_add=True, null=True)
    # One of UserType
    admin_type = models.TextField(default=AdminType.REGULAR_USER)
    problem_permission = models.TextField(default=ProblemPermission.NONE)
    reset_password_token = models.TextField(null=True)
    reset_password_token_expire_time = models.DateTimeField(null=True)
    # SSO auth token
    auth_token = models.TextField(null=True)
    session_keys = JSONField(default=list)
    is_disabled = models.BooleanField(default=False)
    # 구글 계정 고유 ID. 이메일은 바뀔 수 있으므로 sub 로 연결한다.
    google_sub = models.TextField(null=True, unique=True)
    # 학생 계정을 만든 교사. 학급이 바뀌어도 비밀번호 초기화 권한은 여기를 따른다.
    created_by = models.ForeignKey("self", null=True, on_delete=models.SET_NULL,
                                  related_name="created_students")

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def is_admin(self):
        return self.admin_type == AdminType.ADMIN

    def is_super_admin(self):
        return self.admin_type == AdminType.SUPER_ADMIN

    def is_admin_role(self):
        # 교사는 의도적으로 제외한다. /api/admin/* 전체가 열리는 것을 막고
        # 교사 기능은 /api/teacher/* 에서 개별 소유권 검사로 처리한다.
        return self.admin_type in [AdminType.ADMIN, AdminType.SUPER_ADMIN]

    def is_teacher(self):
        return self.admin_type == AdminType.TEACHER

    def can_mgmt_all_problem(self):
        return self.problem_permission == ProblemPermission.ALL

    def is_contest_admin(self, contest):
        return self.is_authenticated and (contest.created_by == self or self.admin_type == AdminType.SUPER_ADMIN)

    class Meta:
        db_table = "user"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # acm_problems_status examples:
    # {
    #     "problems": {
    #         "1": {
    #             "status": JudgeStatus.ACCEPTED,
    #             "_id": "1000"
    #         }
    #     },
    #     "contest_problems": {
    #         "1": {
    #             "status": JudgeStatus.ACCEPTED,
    #             "_id": "1000"
    #         }
    #     }
    # }
    acm_problems_status = JSONField(default=dict)
    # like acm_problems_status, merely add "score" field
    oi_problems_status = JSONField(default=dict)

    real_name = models.TextField(null=True)
    avatar = models.TextField(default=f"{settings.AVATAR_URI_PREFIX}/default.png")
    blog = models.URLField(null=True)
    mood = models.TextField(null=True)
    github = models.TextField(null=True)
    school = models.TextField(null=True)
    major = models.TextField(null=True)
    language = models.TextField(null=True)
    # for ACM
    accepted_number = models.IntegerField(default=0)
    # for OI
    total_score = models.BigIntegerField(default=0)
    submission_number = models.IntegerField(default=0)

    def add_accepted_problem_number(self):
        self.accepted_number = models.F("accepted_number") + 1
        self.save()

    def add_submission_number(self):
        self.submission_number = models.F("submission_number") + 1
        self.save()

    # 计算总分时， 应先减掉上次该题所得分数， 然后再加上本次所得分数
    def add_score(self, this_time_score, last_time_score=None):
        last_time_score = last_time_score or 0
        self.total_score = models.F("total_score") - last_time_score + this_time_score
        self.save()

    class Meta:
        db_table = "user_profile"


class TeacherApplication(models.Model):
    """교사 가입 신청. 승인 이력을 남기기 위해 승인 후에도 보존한다."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher_application")
    status = models.TextField(default=TeacherApplicationStatus.PENDING)
    applied_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True)
    reviewed_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL,
                                    related_name="reviewed_applications")
    note = models.TextField(blank=True, default="")

    class Meta:
        db_table = "teacher_application"
        ordering = ["-applied_at"]
