import re

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


# 학생 계정 아이디는 "c{학급id}-{번호}" 형태다. 구글 가입자가 이 형태의 닉네임을
# 선점하면 이후 학생 계정과 충돌하므로 닉네임에서 예약어로 막는다.
STUDENT_USERNAME_PREFIX = "c"
STUDENT_USERNAME_RE = re.compile(rf"^{STUDENT_USERNAME_PREFIX}\d+-\d+$")


class School(models.Model):
    """나이스(NEIS) 학교 기본정보에서 적재한다.

    학교명을 자유 입력으로 두면 표기가 흔들려("서울초" vs "서울초등학교")
    학생이 자기 학급을 찾지 못한다. 목록에서 고르게 하기 위한 모델이다.
    """
    code = models.TextField(unique=True)            # 나이스 SD_SCHUL_CODE
    name = models.TextField(db_index=True)
    kind = models.TextField(blank=True, default="")     # 초등학교 / 중학교 / 고등학교
    office = models.TextField(blank=True, default="")   # 시도교육청
    address = models.TextField(blank=True, default="")

    class Meta:
        db_table = "school"
        ordering = ["name"]

    def __str__(self):
        return self.name


class SchoolClass(models.Model):
    """학급. 학생 로그인의 진입점이자 문제집 배포 단위다.

    같은 학교·학년·반을 여러 교사가 맡을 수 있어(담임/교과) teacher 까지 포함해 유일하다.
    """
    school = models.ForeignKey(School, on_delete=models.PROTECT, related_name="classes")
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="classes")
    year = models.IntegerField()        # 학년도
    grade = models.IntegerField()       # 학년
    class_no = models.IntegerField()    # 반
    created_at = models.DateTimeField(auto_now_add=True)
    is_archived = models.BooleanField(default=False)

    class Meta:
        db_table = "school_class"
        unique_together = (("school", "teacher", "year", "grade", "class_no"),)
        ordering = ["-year", "grade", "class_no"]

    @property
    def display_name(self):
        return f"{self.year}학년도 {self.grade}학년 {self.class_no}반"

    def student_username(self, number):
        """학생 계정 아이디. 학급 id 로 만들어 전역에서 유일하다.

        교사도 학생도 이 값을 입력하지 않는다(학생은 학교·반·번호로 로그인).
        내부 식별용이므로 사람이 정하게 하지 않는다.
        """
        return f"{STUDENT_USERNAME_PREFIX}{self.id}-{number:02d}"

    def __str__(self):
        return f"{self.school.name} {self.display_name}"


class ClassMembership(models.Model):
    """학급 소속. 학생은 학급 안에서 번호로 식별된다."""
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name="memberships")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="class_memberships")
    number = models.IntegerField()
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "class_membership"
        unique_together = (("school_class", "number"), ("school_class", "student"))
        ordering = ["number"]


def public_display_name(user):
    """공개 화면(순위·제출 목록)에 표시할 이름.

    - 구글 가입자(교사·개인학생): 본인이 정한 닉네임
    - 수업용 학생: 학교명까지만. 학년·반·번호는 노출하지 않는다.
      같은 학교 학생이 여럿이면 서로 구분되지 않는데, 그것이 의도다.
    """
    if user is None:
        return "(삭제된 사용자)"
    membership = next(iter(user.class_memberships.all()), None)
    if membership is not None:
        return f"{membership.school_class.school.name} 학생"
    return user.username


# 표시 이름 계산 시 N+1 을 막기 위한 prefetch 경로 (User 기준)
_DISPLAY_NAME_PATH = "class_memberships__school_class__school"


def display_name_prefetch(user_path=""):
    """표시 이름 계산용 prefetch 경로를 만든다.

    경로가 User 기준이라 어디서 출발하는지 호출부에서 명시해야 한다.
        User 쿼리셋        -> display_name_prefetch()
        Submission 쿼리셋  -> display_name_prefetch("user")
    """
    return f"{user_path}__{_DISPLAY_NAME_PATH}" if user_path else _DISPLAY_NAME_PATH
