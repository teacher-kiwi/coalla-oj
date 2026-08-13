from account.models import has_public_profile, my_student_ids, public_display_name
from .models import Submission
from utils.api import serializers


class CreateSubmissionSerializer(serializers.Serializer):
    problem_id = serializers.IntegerField()
    language = serializers.CharField()  # Block Coding 허용을 위해 CharField로 변경
    code = serializers.CharField(max_length=1024 * 1024)
    contest_id = serializers.IntegerField(required=False)
    captcha = serializers.CharField(required=False)
    blockly_state = serializers.CharField(required=False, allow_blank=True)


class SubmissionModelSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    profile_visible = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = "__all__"

    def get_username(self, obj):
        return public_display_name(obj.user)

    def get_profile_visible(self, obj):
        return has_public_profile(obj.user)


# 채점 상세(info)를 감추는 직렬화기. ACM 규칙에서 쓴다.
class SubmissionSafeModelSerializer(serializers.ModelSerializer):
    problem = serializers.SlugRelatedField(read_only=True, slug_field="_id")
    username = serializers.SerializerMethodField()
    profile_visible = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        exclude = ("info", "contest", "ip")

    def get_username(self, obj):
        return public_display_name(obj.user)

    def get_profile_visible(self, obj):
        return has_public_profile(obj.user)


class SubmissionListSerializer(serializers.ModelSerializer):
    problem = serializers.SlugRelatedField(read_only=True, slug_field="_id")
    show_link = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    profile_visible = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        # 교사가 목록을 볼 때 행마다 "내 학생인가"를 묻지 않도록 한 번만 모아둔다.
        # (Submission.check_user_permission 은 단건용이라 행마다 쿼리를 낸다)
        self._my_student_ids = None
        if self.user is not None and self.user.is_authenticated and self.user.is_teacher():
            self._my_student_ids = set(my_student_ids(self.user))
        super().__init__(*args, **kwargs)

    class Meta:
        model = Submission
        exclude = ("info", "contest", "code", "ip")

    def get_username(self, obj):
        return public_display_name(obj.user)

    def get_profile_visible(self, obj):
        return has_public_profile(obj.user)

    def get_show_link(self, obj):
        if self.user is None or not self.user.is_authenticated:
            return False
        return obj.check_user_permission(self.user, student_ids=self._my_student_ids)


class TeacherStudentSubmissionSerializer(serializers.ModelSerializer):
    """교사가 담당 학생 한 명의 제출 이력을 볼 때 쓴다.

    표시 이름이 필요 없다(누구인지 이미 알고 연 화면이다). 코드는 목록에 싣지 않고
    기존 제출 상세 API 로 연다.
    """
    problem = serializers.SlugRelatedField(read_only=True, slug_field="_id")
    problem_title = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = ("id", "problem", "problem_title", "result", "language",
                  "create_time", "statistic_info")

    def get_problem_title(self, obj):
        return obj.problem.title
