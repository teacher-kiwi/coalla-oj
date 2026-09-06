import re
import secrets

from django.contrib.auth.models import AbstractBaseUser
from django.conf import settings
from django.db import models
from utils.models import JSONField


class AdminType(object):
    REGULAR_USER = "Regular User"
    TEACHER = "Teacher"
    ADMIN = "Admin"
    SUPER_ADMIN = "Super Admin"


# 순위(공개 순위·대회 순위)에 이름이 오르는 계정.
#
# 관리자는 운영자라 뺀다. 교사는 학생과 함께 문제를 푸는 사용자이므로 넣는다.
# 상위 OJ 에는 교사 유형이 없어 "일반 사용자"만 담았고, 교사를 추가한 뒤로
# 교사가 문제를 풀어도 어느 순위에도 나오지 않았다.
RANKED_ADMIN_TYPES = (AdminType.REGULAR_USER, AdminType.TEACHER)


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
    # AdminType 중 하나
    admin_type = models.TextField(default=AdminType.REGULAR_USER)
    problem_permission = models.TextField(default=ProblemPermission.NONE)
    # SSO 인증 토큰
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
    # 푼 문제 현황. 문제 id 를 키로 갖는다(그 id 가 곧 화면에 보이는 문제 번호다).
    # 대회 안 현황은 대회 id 로 한 겹 더 나눈다. 한 문제를 여러 대회에 담을 수 있어서
    # 문제 id 만으로 담으면 대회끼리 섞인다.
    # {"problems": {"1": {"status": JudgeStatus.ACCEPTED}},
    #  "contest_problems": {"3": {"1": {"status": JudgeStatus.ACCEPTED}}}}
    acm_problems_status = JSONField(default=dict)
    # 위와 같고 "score" 가 하나 더 붙는다
    oi_problems_status = JSONField(default=dict)

    # 학교·전공·블로그·GitHub·기분은 6단계에서 제거했다. 입력률이 0이었고,
    # 학교 정보는 학급(SchoolClass)이 대신한다. 실명도 함께 없앴다.
    # 교사가 학생을 알아보는 일은 ClassMembership.nickname 이 대신한다.
    avatar = models.TextField(default=f"{settings.AVATAR_URI_PREFIX}/default.png")
    accepted_number = models.IntegerField(default=0)
    total_score = models.BigIntegerField(default=0)
    submission_number = models.IntegerField(default=0)

    def add_accepted_problem_number(self):
        self.accepted_number = models.F("accepted_number") + 1
        self.save()

    def add_submission_number(self):
        self.submission_number = models.F("submission_number") + 1
        self.save()

    # 총점은 이 문제에서 지난번에 받은 점수를 빼고 이번 점수를 더한다
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


# 학생 계정 아이디는 "학생12345678" 형태다.
#
# 이 값은 순위·채점 목록 등 공개 화면에 그대로 나온다. 그래서 학급이나 번호를
# 담지 않는다. 예전에는 "c{학급id}-{번호}" 였는데, 노출되면 같은 학급 학생이
# 묶이고 번호 순서까지 드러났다. 무작위라 옆 번호를 추측할 수도 없다.
#
# 학생은 이 아이디로 로그인하지 않는다(학교·학년·반·번호 + PIN).
# 사람이 외울 필요가 없으므로 자릿수를 넉넉히 잡아 충돌을 피한다.
STUDENT_USERNAME_PREFIX = "학생"
STUDENT_USERNAME_DIGITS = 8
STUDENT_USERNAME_RE = re.compile(rf"^{STUDENT_USERNAME_PREFIX}\d{{{STUDENT_USERNAME_DIGITS}}}$")

# 구글 가입자가 학생 계정을 사칭하지 못하게 접두어 자체를 막는다.
# 자릿수까지 맞춘 것만 막으면 "학생1" 같은 값이 통과해 헷갈린다.
RESERVED_USERNAME_PREFIX_MESSAGE = "학생 계정 구분을 위해 '학생'으로 시작할 수 없습니다"


def is_reserved_username(value):
    return (value or "").strip().startswith(STUDENT_USERNAME_PREFIX)


def generate_student_usernames(count, taken=None):
    """겹치지 않는 학생 아이디를 count 개 만든다.

    한 학급을 한 번에 만들기 때문에(bulk_create) 서로 간의 충돌도 함께 걸러야 한다.
    DB 의 유니크 제약이 최종 방어선이고, 여기서는 재시도 횟수를 줄이는 정도만 한다.
    """
    pool = set(taken or ())
    pool.update(User.objects.filter(username__startswith=STUDENT_USERNAME_PREFIX)
                .values_list("username", flat=True))
    made = []
    upper = 10 ** STUDENT_USERNAME_DIGITS
    while len(made) < count:
        candidate = f"{STUDENT_USERNAME_PREFIX}{secrets.randbelow(upper):0{STUDENT_USERNAME_DIGITS}d}"
        if candidate in pool:
            continue
        pool.add(candidate)
        made.append(candidate)
    return made


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
    # 교사가 정한 자기 학급의 차례. 대회·문제집의 배포 학급 표가 모두 이 차례를 따른다.
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "school_class"
        unique_together = (("school", "teacher", "year", "grade", "class_no"),)
        # order 는 교사마다 매기는 값이라 기본 정렬에 넣지 않는다. 학생의 학급 고르기는
        # 한 학교의 여러 교사 학급을 함께 보여주므로 섞이면 안 된다.
        # 교사 자기 목록(SchoolClassAPI.get)에서만 order 로 정렬한다.
        ordering = ["-year", "grade", "class_no"]

    @property
    def display_name(self):
        return f"{self.year}학년도 {self.grade}학년 {self.class_no}반"

    def __str__(self):
        return f"{self.school.name} {self.display_name}"


class ClassMembership(models.Model):
    """학급 소속. 학생은 학급 안에서 번호로 식별된다."""
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name="memberships")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="class_memberships")
    number = models.IntegerField()
    # 교사가 학생을 알아보기 위한 이름. 공개 화면에는 나가지 않는다.
    # 담당 교사와 본인만 본다. 학급마다 따로 붙이는 값이라 여기에 둔다.
    # 실명을 적을 수도 있어 중복을 막지 않는다(같은 이름이 여러 학급에 있을 수 있다).
    nickname = models.TextField()
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "class_membership"
        unique_together = (("school_class", "number"), ("school_class", "student"))
        ordering = ["number"]


def my_student_ids(teacher):
    """교사가 담당하는 학급에 속한 학생 id.

    "내 학생만 보기" 필터와 교사 권한 검사가 같은 기준을 쓰도록 한 곳에 둔다.
    """
    return ClassMembership.objects.filter(school_class__teacher=teacher) \
                                  .values_list("student_id", flat=True)


def my_student_nicknames(user):
    """{학생 id: 닉네임}. 담당 교사가 아니면 빈 dict.

    공개 목록(순위·채점 현황)에서 교사가 자기 학생만 알아볼 수 있게 한다.
    행마다 조회하지 않도록 한 번에 모아 온다.
    """
    if not (user is not None and user.is_authenticated and user.is_teacher()):
        return {}
    rows = ClassMembership.objects.filter(school_class__teacher=user) \
                                  .values_list("student_id", "nickname")
    return dict(rows)
