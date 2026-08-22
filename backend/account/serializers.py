from django import forms

from utils.api import serializers, UsernameSerializer

from .models import (AdminType, ClassMembership, ProblemPermission,
                     RESERVED_USERNAME_PREFIX_MESSAGE, School, SchoolClass,
                     TeacherApplication, TeacherApplicationStatus, User,
                     UserProfile, is_reserved_username)


def reject_reserved_username(value):
    """학생 계정 아이디("학생...")를 사람이 선점하지 못하게 막는다.

    구글 가입뿐 아니라 관리자의 사용자 편집·CSV 가져오기·대량 생성에도 걸어야
    한다. 한 곳만 막으면 나머지 경로로 학생을 사칭하는 계정이 만들어진다.
    """
    if is_reserved_username(value):
        raise serializers.ValidationError(RESERVED_USERNAME_PREFIX_MESSAGE)
    return value


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class UserChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=6)


class GenerateUserSerializer(serializers.Serializer):
    prefix = serializers.CharField(max_length=16, allow_blank=True)
    suffix = serializers.CharField(max_length=16, allow_blank=True)
    number_from = serializers.IntegerField()
    number_to = serializers.IntegerField()
    password_length = serializers.IntegerField(max_value=16, default=8)

    def validate(self, attrs):
        # 만들어질 아이디는 prefix + 번호 + suffix 다. 조합 결과를 봐야 한다.
        reject_reserved_username(attrs["prefix"])
        return attrs


class ImportUserSeralizer(serializers.Serializer):
    users = serializers.ListField(
        child=serializers.ListField(child=serializers.CharField(max_length=64)))

    def validate_users(self, value):
        for row in value:
            if row:
                reject_reserved_username(row[0])
        return value


class UserAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "admin_type", "problem_permission",
                  "create_time", "last_login", "is_disabled"]


class UserSerializer(serializers.ModelSerializer):
    # 구글로 가입했는지만 알려준다. sub 자체는 내부 식별자라 내보내지 않는다.
    # 화면에서 "회원 탈퇴"를 보여줄지 판단하는 데 쓴다.
    is_google_account = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "admin_type", "problem_permission",
                  "create_time", "last_login", "is_disabled", "created_by",
                  "is_google_account"]

    def get_is_google_account(self, obj):
        return bool(obj.google_sub)


# 남이 볼 수 있는 프로필에 실리는 사용자 필드. 화면이 쓰는 것만 남긴다.
#
# 예전에는 UserSerializer 를 통째로 중첩하고 fields="__all__" 이었다. 수업용
# 학생 프로필이 막혀 있어 드러나지 않았을 뿐, 열고 나면 created_by(담당 교사 id)
# 로 학생들을 학급 단위로 묶어볼 수 있고 last_login 같은 활동 기록도 함께 나간다.
_PUBLIC_USER_FIELDS = ("id", "username")
# 푼 문제 목록(acm/oi_problems_status)은 사용자 홈이 "해결한 문제"를 그리는 데 쓴다.
# 이미 공개된 accepted_number 를 문제별로 늘어놓은 것이라 새로 드러나는 정보는 없다.
_PUBLIC_PROFILE_FIELDS = ("avatar", "accepted_number", "submission_number", "total_score",
                          "acm_problems_status", "oi_problems_status")


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = UserProfile
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        # 본인이 자기 프로필을 볼 때만 전부 내려준다.
        self.show_private = kwargs.pop("show_private", False)
        super(UserProfileSerializer, self).__init__(*args, **kwargs)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.show_private:
            # 자기 화면(NavBar)에서 "닉네임(아이디)" 로 보여주기 위한 값.
            # 순위·채점 목록에서 자기를 찾으려면 자기 아이디를 알아야 한다.
            data["nickname"] = _own_nickname(instance.user)
            return data
        user = data.get("user") or {}
        return {
            **{k: data[k] for k in _PUBLIC_PROFILE_FIELDS if k in data},
            "user": {k: user[k] for k in _PUBLIC_USER_FIELDS if k in user},
        }


def _own_nickname(user):
    """수업용 학생이면 학급 소속의 닉네임. 그 외에는 None."""
    membership = user.class_memberships.first()
    return membership.nickname if membership else None


class EditUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField(max_length=32, validators=[reject_reserved_username])
    password = serializers.CharField(min_length=6, allow_blank=True, required=False, default=None)
    email = serializers.EmailField(max_length=64)
    admin_type = serializers.ChoiceField(choices=(AdminType.REGULAR_USER, AdminType.ADMIN, AdminType.SUPER_ADMIN))
    problem_permission = serializers.ChoiceField(choices=(ProblemPermission.NONE, ProblemPermission.OWN,
                                                          ProblemPermission.ALL))
    is_disabled = serializers.BooleanField()


class EditUserProfileSerializer(serializers.Serializer):
    avatar = serializers.CharField(max_length=256, allow_blank=True, required=False)


class SSOSerializer(serializers.Serializer):
    token = serializers.CharField()


class GoogleLoginSerializer(serializers.Serializer):
    credential = serializers.CharField(max_length=4096)
    # 최초 가입 시에만 필요하다. 없으면 서버가 nickname_required 로 응답한다.
    nickname = serializers.CharField(max_length=20, required=False, allow_blank=True)


class DeleteAccountSerializer(serializers.Serializer):
    # 탈퇴 직전에 구글로 다시 로그인해 받은 토큰. 지금 로그인한 계정과 같은지 대조한다.
    credential = serializers.CharField(max_length=4096)


class TeacherApplicationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    reviewed_by = serializers.CharField(source="reviewed_by.username", read_only=True, default=None)

    class Meta:
        model = TeacherApplication
        fields = ["id", "username", "email", "status",
                  "applied_at", "reviewed_at", "reviewed_by", "note"]


class ReviewTeacherApplicationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=(TeacherApplicationStatus.APPROVED,
                                              TeacherApplicationStatus.REJECTED))
    note = serializers.CharField(max_length=256, allow_blank=True, required=False)


class ImageUploadForm(forms.Form):
    image = forms.FileField()


class FileUploadForm(forms.Form):
    file = forms.FileField()


class RankInfoSerializer(serializers.ModelSerializer):
    user = UsernameSerializer()

    class Meta:
        model = UserProfile
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        # 담당 교사가 순위를 볼 때만 자기 학생의 닉네임을 함께 내려준다.
        # 중첩 필드는 인스턴스마다 따로 복제되므로 여기서 채워도 안전하다.
        nicknames = kwargs.pop("nicknames", None)
        super().__init__(*args, **kwargs)
        self.fields["user"].nicknames = nicknames or {}


# ---------------- 학교 / 학급 / 학생 ----------------

class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ["id", "code", "name", "kind", "office"]


class SchoolClassSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source="school.name", read_only=True)
    teacher_name = serializers.CharField(source="teacher.username", read_only=True)
    display_name = serializers.CharField(read_only=True)
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = SchoolClass
        fields = ["id", "school", "school_name", "teacher_name", "year", "grade",
                  "class_no", "display_name", "student_count",
                  "is_archived", "created_at"]

    def get_student_count(self, obj):
        return obj.memberships.count()


class CreateSchoolClassSerializer(serializers.Serializer):
    school = serializers.IntegerField()
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    grade = serializers.IntegerField(min_value=1, max_value=6)
    class_no = serializers.IntegerField(min_value=1, max_value=99)


class EditSchoolClassSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    year = serializers.IntegerField(min_value=2000, max_value=2100, required=False)
    grade = serializers.IntegerField(min_value=1, max_value=6, required=False)
    class_no = serializers.IntegerField(min_value=1, max_value=99, required=False)
    is_archived = serializers.BooleanField(required=False)


class CreateStudentsSerializer(serializers.Serializer):
    school_class = serializers.IntegerField()
    number_from = serializers.IntegerField(min_value=1, max_value=99)
    number_to = serializers.IntegerField(min_value=1, max_value=99)


class ClassMembershipSerializer(serializers.ModelSerializer):
    student_id = serializers.IntegerField(source="student.id", read_only=True)
    # 교사가 순위·채점 목록에서 학생을 찾으려면 공개 아이디를 알아야 한다
    username = serializers.CharField(source="student.username", read_only=True)
    is_disabled = serializers.BooleanField(source="student.is_disabled", read_only=True)
    last_login = serializers.DateTimeField(source="student.last_login", read_only=True)

    class Meta:
        model = ClassMembership
        fields = ["id", "number", "nickname", "username", "student_id",
                  "is_disabled", "last_login", "joined_at"]


class EditStudentNicknameSerializer(serializers.Serializer):
    membership = serializers.IntegerField()
    nickname = serializers.CharField(max_length=32)


class ResetStudentPasswordSerializer(serializers.Serializer):
    membership = serializers.IntegerField()


class StudentLoginSerializer(serializers.Serializer):
    school_class = serializers.IntegerField()
    number = serializers.IntegerField(min_value=1, max_value=99)
    password = serializers.RegexField(r"^\d{4}$")


class StudentChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.RegexField(r"^\d{4}$")
    new_password = serializers.RegexField(r"^\d{4}$")
