from django import forms

from utils.api import serializers, UsernameSerializer

from .models import (AdminType, ClassMembership, ProblemPermission, School,
                     SchoolClass, TeacherApplication, TeacherApplicationStatus,
                     User, UserProfile)


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class UsernameOrEmailCheckSerializer(serializers.Serializer):
    username = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)


class UserChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=6)


class UserChangeEmailSerializer(serializers.Serializer):
    password = serializers.CharField()
    new_email = serializers.EmailField(max_length=64)


class GenerateUserSerializer(serializers.Serializer):
    prefix = serializers.CharField(max_length=16, allow_blank=True)
    suffix = serializers.CharField(max_length=16, allow_blank=True)
    number_from = serializers.IntegerField()
    number_to = serializers.IntegerField()
    password_length = serializers.IntegerField(max_value=16, default=8)


class ImportUserSeralizer(serializers.Serializer):
    users = serializers.ListField(
        child=serializers.ListField(child=serializers.CharField(max_length=64)))


class UserAdminSerializer(serializers.ModelSerializer):
    real_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "admin_type", "problem_permission", "real_name",
                  "create_time", "last_login", "is_disabled"]

    def get_real_name(self, obj):
        return obj.userprofile.real_name


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


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    real_name = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        self.show_real_name = kwargs.pop("show_real_name", False)
        super(UserProfileSerializer, self).__init__(*args, **kwargs)

    def get_real_name(self, obj):
        return obj.real_name if self.show_real_name else None


class EditUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField(max_length=32)
    real_name = serializers.CharField(max_length=32, allow_blank=True, allow_null=True)
    password = serializers.CharField(min_length=6, allow_blank=True, required=False, default=None)
    email = serializers.EmailField(max_length=64)
    admin_type = serializers.ChoiceField(choices=(AdminType.REGULAR_USER, AdminType.ADMIN, AdminType.SUPER_ADMIN))
    problem_permission = serializers.ChoiceField(choices=(ProblemPermission.NONE, ProblemPermission.OWN,
                                                          ProblemPermission.ALL))
    is_disabled = serializers.BooleanField()


class EditUserProfileSerializer(serializers.Serializer):
    real_name = serializers.CharField(max_length=32, allow_null=True, required=False)
    avatar = serializers.CharField(max_length=256, allow_blank=True, required=False)


class ApplyResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    captcha = serializers.CharField()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(min_length=6)
    captcha = serializers.CharField()


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
    real_name = serializers.SerializerMethodField()
    reviewed_by = serializers.CharField(source="reviewed_by.username", read_only=True, default=None)

    class Meta:
        model = TeacherApplication
        fields = ["id", "username", "email", "real_name", "status",
                  "applied_at", "reviewed_at", "reviewed_by", "note"]

    def get_real_name(self, obj):
        profile = UserProfile.objects.filter(user=obj.user).first()
        return profile.real_name if profile else None


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
    is_disabled = serializers.BooleanField(source="student.is_disabled", read_only=True)
    last_login = serializers.DateTimeField(source="student.last_login", read_only=True)

    class Meta:
        model = ClassMembership
        fields = ["id", "number", "student_id", "is_disabled", "last_login", "joined_at"]


class ResetStudentPasswordSerializer(serializers.Serializer):
    membership = serializers.IntegerField()


class StudentLoginSerializer(serializers.Serializer):
    school_class = serializers.IntegerField()
    number = serializers.IntegerField(min_value=1, max_value=99)
    password = serializers.RegexField(r"^\d{4}$")


class StudentChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.RegexField(r"^\d{4}$")
    new_password = serializers.RegexField(r"^\d{4}$")
