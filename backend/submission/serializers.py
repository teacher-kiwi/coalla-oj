from account.models import my_student_nicknames
from .models import Submission
from utils.api import serializers


class CreateSubmissionSerializer(serializers.Serializer):
    problem_id = serializers.IntegerField()
    language = serializers.CharField()  # Block Coding 허용을 위해 CharField로 변경
    code = serializers.CharField(max_length=1024 * 1024)
    contest_id = serializers.IntegerField(required=False)
    blockly_state = serializers.CharField(required=False, allow_blank=True)


class _AuthorMixin:
    """작성자 표시. 학생 아이디는 무작위라 그대로 내보내도 아무것도 드러나지 않는다.

    담당 교사가 볼 때만 nickname 을 함께 실어 자기 학생을 알아보게 한다.
    """
    def get_username(self, obj):
        return obj.user.username

    def get_nickname(self, obj):
        return self._nicknames.get(obj.user_id)


class SubmissionModelSerializer(_AuthorMixin, serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    nickname = serializers.SerializerMethodField()
    _nicknames = {}

    class Meta:
        model = Submission
        fields = "__all__"


# 채점 상세(info)를 감추는 직렬화기. ACM 규칙에서 쓴다.
class SubmissionSafeModelSerializer(_AuthorMixin, serializers.ModelSerializer):
    problem = serializers.SlugRelatedField(read_only=True, slug_field="display_id")
    username = serializers.SerializerMethodField()
    nickname = serializers.SerializerMethodField()
    _nicknames = {}

    class Meta:
        model = Submission
        exclude = ("info", "contest", "ip")


class SubmissionListSerializer(_AuthorMixin, serializers.ModelSerializer):
    problem = serializers.SlugRelatedField(read_only=True, slug_field="display_id")
    show_link = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    nickname = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        # 교사가 목록을 볼 때 행마다 "내 학생인가"를 묻지 않도록 한 번만 모아둔다.
        # (Submission.check_user_permission 은 단건용이라 행마다 쿼리를 낸다)
        self._my_student_ids = None
        self._nicknames = my_student_nicknames(self.user)
        if self._nicknames:
            self._my_student_ids = set(self._nicknames)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Submission
        # 필요한 것만 싣는다. exclude 로 두면 모델에 필드가 늘 때마다 따라 나간다.
        fields = ("id", "problem", "create_time", "result", "language",
                  "statistic_info", "username", "nickname", "show_link")

    def get_show_link(self, obj):
        if self.user is None or not self.user.is_authenticated:
            return False
        return obj.check_user_permission(self.user, student_ids=self._my_student_ids)


class TeacherStudentSubmissionSerializer(serializers.ModelSerializer):
    """교사가 담당 학생 한 명의 제출 이력을 볼 때 쓴다.

    표시 이름이 필요 없다(누구인지 이미 알고 연 화면이다). 코드는 목록에 싣지 않고
    기존 제출 상세 API 로 연다.
    """
    problem = serializers.SlugRelatedField(read_only=True, slug_field="display_id")
    problem_title = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = ("id", "problem", "problem_title", "result", "language",
                  "create_time", "statistic_info")

    def get_problem_title(self, obj):
        return obj.problem.title
