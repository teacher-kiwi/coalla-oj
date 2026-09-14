import re

from django import forms

from options.options import SysOptions
from utils.api import UsernameSerializer, serializers
from utils.constants import Difficulty
from utils.serializers import LanguageNameMultiChoiceField, SPJLanguageNameChoiceField, LanguageNameChoiceField

from .models import (Problem, ProblemIOMode, ProblemRuleType, ProblemSet,
                     ProblemSetAssignment, ProblemSetItem, ProblemTag)
from .utils import parse_problem_template


class TestCaseUploadForm(forms.Form):
    spj = forms.CharField(max_length=12)
    file = forms.FileField()


# 예제는 문제를 여는 모든 학생에게 매번 전송되므로 크기와 개수를 제한한다.
MAX_SAMPLES = 3
MAX_SAMPLE_BYTES = 2 * 1024
# 손으로 넣는 테스트케이스. 많거나 크면 zip 으로 올리는 게 맞다.
MAX_CASES = 20
MAX_CASE_BYTES = 64 * 1024


class CreateSampleSerializer(serializers.Serializer):
    input = serializers.CharField(trim_whitespace=False)
    output = serializers.CharField(trim_whitespace=False)


class TeacherTestCaseSerializer(serializers.Serializer):
    """테스트케이스 한 줄. 교사·관리자 화면이 함께 쓴다.

    keep 은 화면이 내용을 불러오지 못한 케이스다(너무 커서 표에서 못 고친다).
    그 번호의 파일을 이전 묶음에서 그대로 옮긴다. 내용을 보내지 않으므로
    "새로 입력한 케이스" 개수에도 세지 않는다.
    """
    input = serializers.CharField(max_length=MAX_CASE_BYTES, allow_blank=True,
                                  trim_whitespace=False, required=False)
    output = serializers.CharField(max_length=MAX_CASE_BYTES, allow_blank=True,
                                   trim_whitespace=False, required=False)
    keep = serializers.IntegerField(min_value=1, required=False)

    def validate(self, data):
        if not data.get("keep") and data.get("input") is None:
            raise serializers.ValidationError("테스트 케이스의 입력이 없습니다")
        return data


class CreateTestCaseScoreSerializer(serializers.Serializer):
    input_name = serializers.CharField(max_length=32)
    output_name = serializers.CharField(max_length=32)
    score = serializers.IntegerField(min_value=0)


class ProblemIOModeSerializer(serializers.Serializer):
    io_mode = serializers.ChoiceField(choices=ProblemIOMode.choices())
    input = serializers.CharField()
    output = serializers.CharField()

    def validate(self, attrs):
        if attrs["input"] == attrs["output"]:
            raise serializers.ValidationError("입력 파일명과 출력 파일명이 같을 수 없습니다")
        for item in (attrs["input"], attrs["output"]):
            if not re.match("^[a-zA-Z0-9.]+$", item):
                raise serializers.ValidationError("파일명은 영문·숫자·마침표만 사용할 수 있습니다")
        return attrs


class CreateOrEditProblemSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=1024)
    description = serializers.CharField()
    # 입력이 없는 문제("Hello World 출력하기")도 있어 비워둘 수 있다.
    # 교사 출제 화면(TeacherProblemSerializer)도 같은 규칙이다. 여기서만 막으면
    # 교사가 비워 만든 문제를 관리자가 저장할 수 없다(공개 스위치를 켜는 것도 저장이다).
    input_description = serializers.CharField(allow_blank=True)
    output_description = serializers.CharField(allow_blank=True)
    samples = serializers.ListField(child=CreateSampleSerializer(), allow_empty=False)
    # 테스트케이스를 넣는 두 가지 길. 파일로 올렸으면 업로드가 돌려준
    # test_case_id 와 배점이 오고, 직접 입력이면 cases 가 온다.
    test_case_id = serializers.CharField(max_length=32, required=False, allow_blank=True)
    test_case_score = serializers.ListField(child=CreateTestCaseScoreSerializer(),
                                            allow_empty=True, required=False)
    cases = serializers.ListField(child=TeacherTestCaseSerializer(), required=False)
    time_limit = serializers.IntegerField(min_value=1, max_value=1000 * 60)
    memory_limit = serializers.IntegerField(min_value=1, max_value=1024)
    languages = LanguageNameMultiChoiceField()
    template = serializers.DictField(child=serializers.CharField(min_length=1))
    rule_type = serializers.ChoiceField(choices=[ProblemRuleType.ACM, ProblemRuleType.OI])
    io_mode = ProblemIOModeSerializer()
    spj = serializers.BooleanField()
    spj_language = SPJLanguageNameChoiceField(allow_blank=True, allow_null=True)
    spj_code = serializers.CharField(allow_blank=True, allow_null=True)
    spj_compile_ok = serializers.BooleanField(default=False)
    visible = serializers.BooleanField()
    difficulty = serializers.ChoiceField(choices=Difficulty.choices())
    tags = serializers.ListField(child=serializers.CharField(max_length=32), allow_empty=False)
    hint = serializers.CharField(allow_blank=True, allow_null=True)
    source = serializers.CharField(max_length=256, allow_blank=True, allow_null=True)
    # 정답 코드. 넣지 않아도 되고, 넣어도 저장을 막지 않는다.
    solver_language = LanguageNameChoiceField(required=False, allow_blank=True, allow_null=True)
    solver_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    # 저장 전에 검증했으면 그 표. 서버가 지문을 대조해 맞을 때만 결과를 붙인다.
    verification_token = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data.get("cases") and data.get("test_case_id"):
            raise serializers.ValidationError(
                "테스트 케이스는 직접 입력과 파일 중 하나로만 넣을 수 있습니다")
        if not data.get("cases") and not data.get("test_case_id"):
            raise serializers.ValidationError("테스트 케이스를 넣어주세요")
        return data


class CreateProblemSerializer(CreateOrEditProblemSerializer):
    pass


class EditProblemSerializer(CreateOrEditProblemSerializer):
    id = serializers.IntegerField()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProblemTag
        fields = "__all__"


class CreateProblemTagSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=32)
    aliases = serializers.ListField(child=serializers.CharField(max_length=64), allow_empty=True, required=False)


class EditProblemTagSerializer(CreateProblemTagSerializer):
    id = serializers.IntegerField()


class CompileSPJSerializer(serializers.Serializer):
    spj_language = SPJLanguageNameChoiceField()
    spj_code = serializers.CharField()


class BaseProblemSerializer(serializers.ModelSerializer):
    tags = serializers.SlugRelatedField(many=True, slug_field="name", read_only=True)
    created_by = UsernameSerializer()
    # 화면에 보이는 번호. 공개 문제는 pk, 대회 문제는 order 로 만든 A, B, C 다.
    display_id = serializers.ReadOnlyField()

    def get_public_template(self, obj):
        ret = {}
        for lang, code in obj.template.items():
            ret[lang] = parse_problem_template(code)["template"]
        return ret


class ProblemAdminSerializer(BaseProblemSerializer):
    class Meta:
        model = Problem
        fields = "__all__"


class ProblemSerializer(BaseProblemSerializer):
    template = serializers.SerializerMethodField("get_public_template")

    class Meta:
        model = Problem
        # solver_code 는 이 문제의 정답이다. 나가면 학생이 그대로 낸다.
        exclude = ("test_case_score", "test_case_id", "visible",
                   "spj_code", "spj_version", "spj_compile_ok",
                   "solver_code", "solver_language")


class _ContestProblemSerializer(serializers.Serializer):
    """대회 화면용. 문제를 그대로 싣되 번호와 통계만 대회 것으로 바꾼다.

    문제 자체의 누적 통계를 그대로 보여주면, 예전에 공개로 풀린 횟수가 대회
    화면에 나와 난이도가 샌다.
    """
    problem_serializer = None

    def to_representation(self, entry):
        data = self.problem_serializer(entry.problem).data
        data["display_id"] = entry.label
        data["submission_number"] = entry.submission_number
        data["accepted_number"] = entry.accepted_number
        return data


class ProblemListSerializer(serializers.ModelSerializer):
    """목록 화면용. 본문·힌트·예제·코드 템플릿은 상세 API 에서 받는다.

    목록에 전문을 실으면 한 페이지에 문제 본문이 10개씩 실려 나간다.
    rule_type 은 화면에 쓰이진 않지만 "내가 푼 문제" 표시(_add_problem_status)에 필요하다.
    """
    tags = serializers.SlugRelatedField(many=True, slug_field="name", read_only=True)
    display_id = serializers.ReadOnlyField()

    class Meta:
        model = Problem
        fields = ("id", "display_id", "title", "difficulty", "tags", "rule_type", "visibility",
                  "submission_number", "accepted_number")


class ProblemSafeSerializer(BaseProblemSerializer):
    template = serializers.SerializerMethodField("get_public_template")

    class Meta:
        model = Problem
        exclude = ("test_case_score", "test_case_id", "visible",
                   "spj_code", "spj_version", "spj_compile_ok",
                   "difficulty", "submission_number", "accepted_number", "statistic_info")


class ContestProblemAdminSerializer(_ContestProblemSerializer):
    problem_serializer = ProblemAdminSerializer


class ContestProblemDetailSerializer(_ContestProblemSerializer):
    problem_serializer = ProblemSerializer


class ContestProblemSafeSerializer(_ContestProblemSerializer):
    """대회 중 채점 상세를 감출 때 쓴다(ACM 규칙)."""
    problem_serializer = ProblemSafeSerializer


class ExportProblemSerializer(serializers.ModelSerializer):
    display_id = serializers.ReadOnlyField()
    description = serializers.SerializerMethodField()
    input_description = serializers.SerializerMethodField()
    output_description = serializers.SerializerMethodField()
    test_case_score = serializers.SerializerMethodField()
    hint = serializers.SerializerMethodField()
    spj = serializers.SerializerMethodField()
    template = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()
    tags = serializers.SlugRelatedField(many=True, slug_field="name", read_only=True)

    def _html_format_value(self, value):
        return {"format": "html", "value": value}

    def get_description(self, obj):
        return self._html_format_value(obj.description)

    def get_input_description(self, obj):
        return self._html_format_value(obj.input_description)

    def get_output_description(self, obj):
        return self._html_format_value(obj.output_description)

    def get_hint(self, obj):
        return self._html_format_value(obj.hint)

    def get_test_case_score(self, obj):
        return [{"score": item["score"] if obj.rule_type == ProblemRuleType.OI else 100,
                 "input_name": item["input_name"], "output_name": item["output_name"]}
                for item in obj.test_case_score]

    def get_spj(self, obj):
        return {"code": obj.spj_code,
                "language": obj.spj_language} if obj.spj else None

    def get_template(self, obj):
        ret = {}
        for k, v in obj.template.items():
            ret[k] = parse_problem_template(v)
        return ret

    def get_source(self, obj):
        return obj.source or f"{SysOptions.website_name} {SysOptions.website_base_url}"

    class Meta:
        model = Problem
        fields = ("display_id", "title", "description", "tags",
                  "input_description", "output_description",
                  "test_case_score", "hint", "time_limit", "memory_limit", "samples",
                  "template", "spj", "rule_type", "source", "template")


class AddContestProblemSerializer(serializers.Serializer):
    contest_id = serializers.IntegerField()
    problem_id = serializers.IntegerField()


class ExportProblemRequestSerialzier(serializers.Serializer):
    problem_id = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)


class UploadProblemForm(forms.Form):
    file = forms.FileField()


class FormatValueSerializer(serializers.Serializer):
    format = serializers.ChoiceField(choices=["html", "markdown"])
    value = serializers.CharField(allow_blank=True)


class TestCaseScoreSerializer(serializers.Serializer):
    score = serializers.IntegerField(min_value=1)
    input_name = serializers.CharField(max_length=32)
    output_name = serializers.CharField(max_length=32)


class TemplateSerializer(serializers.Serializer):
    prepend = serializers.CharField()
    template = serializers.CharField()
    append = serializers.CharField()


class SPJSerializer(serializers.Serializer):
    code = serializers.CharField()
    language = SPJLanguageNameChoiceField()


class AnswerSerializer(serializers.Serializer):
    code = serializers.CharField()
    language = LanguageNameChoiceField()


class ImportProblemSerializer(serializers.Serializer):
    # 파일에 실려 오지만 쓰지 않는다. 번호는 받는 쪽에서 pk 로 새로 붙는다.
    display_id = serializers.CharField(max_length=128, required=False, allow_blank=True)
    title = serializers.CharField(max_length=128)
    description = FormatValueSerializer()
    input_description = FormatValueSerializer()
    output_description = FormatValueSerializer()
    hint = FormatValueSerializer()
    test_case_score = serializers.ListField(child=TestCaseScoreSerializer(), allow_null=True)
    time_limit = serializers.IntegerField(min_value=1, max_value=60000)
    memory_limit = serializers.IntegerField(min_value=1, max_value=10240)
    samples = serializers.ListField(child=CreateSampleSerializer())
    template = serializers.DictField(child=TemplateSerializer())
    spj = SPJSerializer(allow_null=True)
    rule_type = serializers.ChoiceField(choices=ProblemRuleType.choices())
    source = serializers.CharField(max_length=200, allow_blank=True, allow_null=True)
    answers = serializers.ListField(child=AnswerSerializer())
    tags = serializers.ListField(child=serializers.CharField(max_length=32), allow_empty=False)


# ---- 교사 출제 ----


class TeacherSampleSerializer(serializers.Serializer):
    """학생에게 보여줄 예제.

    화면이 테스트케이스의 내용을 여기에 복사해 넣어 주지만, 그 뒤 교사가 고칠
    수 있다. 그래서 서버는 케이스 번호가 아니라 최종 글자만 받는다.
    번호를 저장하면 손으로 고친 순간 거짓이 된다.
    """
    input = serializers.CharField(max_length=MAX_SAMPLE_BYTES, allow_blank=True,
                                  trim_whitespace=False)
    output = serializers.CharField(max_length=MAX_SAMPLE_BYTES, allow_blank=True,
                                   trim_whitespace=False)


class TeacherProblemSerializer(serializers.Serializer):
    """교사용 간단 출제.

    표시 번호·시간 제한·메모리 제한·특수 채점·코드 템플릿은 받지 않는다.
    서버가 기본값을 채운다.
    """
    title = serializers.CharField(max_length=1024)
    description = serializers.CharField()
    input_description = serializers.CharField(allow_blank=True)
    output_description = serializers.CharField(allow_blank=True)
    hint = serializers.CharField(allow_blank=True, required=False, default="")
    difficulty = serializers.ChoiceField(choices=Difficulty.choices())
    tags = serializers.ListField(child=serializers.CharField(max_length=32), allow_empty=False)
    samples = serializers.ListField(child=TeacherSampleSerializer(), allow_empty=False)
    # 테스트케이스를 넣는 두 가지 길. 직접 입력이면 cases, 파일로 올렸으면
    # 업로드가 돌려준 test_case_id 가 온다. 만들 때는 둘 중 하나가 있어야 한다.
    cases = serializers.ListField(child=TeacherTestCaseSerializer(), required=False)
    test_case_id = serializers.CharField(max_length=32, required=False)
    # 채점 방식. 특수 채점은 정답 파일 대신 judge 코드가 판정한다
    # ("4보다 작은 수를 모두 출력" 처럼 답이 여럿인 문제).
    spj = serializers.BooleanField(default=False)
    spj_language = SPJLanguageNameChoiceField(required=False, allow_blank=True, allow_null=True)
    spj_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    # 정답 코드. 넣지 않아도 되고, 넣어도 저장을 막지 않는다.
    solver_language = LanguageNameChoiceField(required=False, allow_blank=True, allow_null=True)
    solver_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    # 저장 전에 검증했으면 그 표. 서버가 지문을 대조해 맞을 때만 결과를 붙인다.
    verification_token = serializers.CharField(required=False, allow_blank=True)

    def validate_cases(self, cases):
        if not cases:
            raise serializers.ValidationError("테스트 케이스를 하나 이상 넣어주세요")
        # 불러온 그대로 돌려보내는 것(keep)은 세지 않는다. 상한은 사람이 표에
        # 직접 쳐 넣는 양을 막으려는 것이지, 이미 있던 케이스를 막는 것이 아니다.
        typed = [c for c in cases if not c.get("keep")]
        if len(typed) > MAX_CASES:
            raise serializers.ValidationError(
                f"직접 입력하는 테스트 케이스는 {MAX_CASES}개까지입니다. "
                "더 많으면 파일로 올려주세요")
        return cases

    def validate_samples(self, samples):
        if len(samples) > MAX_SAMPLES:
            raise serializers.ValidationError(f"예제는 {MAX_SAMPLES}개까지 넣을 수 있습니다")
        return samples

    def validate(self, data):
        if data.get("cases") and data.get("test_case_id"):
            raise serializers.ValidationError(
                "테스트 케이스는 직접 입력과 파일 중 하나로만 넣을 수 있습니다")
        if data.get("spj") and not (data.get("spj_language") and data.get("spj_code")):
            raise serializers.ValidationError("판정 코드와 언어를 넣어주세요")
        return data


class CreateTeacherProblemSerializer(TeacherProblemSerializer):
    def validate(self, data):
        data = super().validate(data)
        if not data.get("cases") and not data.get("test_case_id"):
            raise serializers.ValidationError("테스트 케이스를 넣어주세요")
        return data


class EditTeacherProblemSerializer(TeacherProblemSerializer):
    """고칠 때는 케이스를 다시 보내지 않으면 있던 것을 그대로 둔다."""
    id = serializers.IntegerField()


class ReviewProblemPublishSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    approve = serializers.BooleanField()


class TeacherProblemListSerializer(serializers.ModelSerializer):
    """교사가 자기 문제를 관리하는 목록용."""
    tags = serializers.SlugRelatedField(many=True, slug_field="name", read_only=True)
    display_id = serializers.ReadOnlyField()

    class Meta:
        model = Problem
        fields = ("id", "display_id", "title", "difficulty", "tags", "visibility", "visible",
                  "create_time", "submission_number", "accepted_number")


# ---- 문제집 ----

class ProblemBriefSerializer(serializers.ModelSerializer):
    """문제집 화면용 요약. 본문·테스트케이스는 기존 문제 상세 API 에서 받는다."""
    display_id = serializers.ReadOnlyField()

    class Meta:
        model = Problem
        fields = ("id", "display_id", "title", "difficulty", "submission_number", "accepted_number")


class ProblemSetItemSerializer(serializers.ModelSerializer):
    problem = ProblemBriefSerializer()
    # 교사가 담아둔 문제가 그동안 감춰졌는지(관리자 조치) 또는 비공개인지 알려준다.
    # 그래야 교사가 문제집에서 빼거나 자기 문제를 고쳐 다시 공개 신청할 수 있다.
    problem_visible = serializers.BooleanField(source="problem.visible", read_only=True)
    problem_visibility = serializers.CharField(source="problem.visibility", read_only=True)

    class Meta:
        model = ProblemSetItem
        fields = ("id", "order", "problem", "problem_visible", "problem_visibility")


class ProblemSetAssignmentSerializer(serializers.ModelSerializer):
    class_name = serializers.SerializerMethodField()

    class Meta:
        model = ProblemSetAssignment
        fields = ("id", "school_class", "class_name", "assigned_at")

    def get_class_name(self, obj):
        return f"{obj.school_class.school.name} {obj.school_class.display_name}"


class ProblemSetSerializer(serializers.ModelSerializer):
    # 목록은 annotate 로 미리 세어 N+1 을 피하고, 생성·수정 응답처럼
    # annotate 가 없는 단건에서는 그때 센다.
    problem_count = serializers.SerializerMethodField()
    assignment_count = serializers.SerializerMethodField()

    def get_problem_count(self, obj):
        count = getattr(obj, "problem_count", None)
        return obj.items.count() if count is None else count

    def get_assignment_count(self, obj):
        count = getattr(obj, "assignment_count", None)
        return obj.assignments.count() if count is None else count

    class Meta:
        model = ProblemSet
        fields = ("id", "title", "description", "create_time", "last_update_time",
                  "problem_count", "assignment_count")


class ProblemSetDetailSerializer(serializers.ModelSerializer):
    items = ProblemSetItemSerializer(many=True)
    assignments = ProblemSetAssignmentSerializer(many=True)

    class Meta:
        model = ProblemSet
        fields = ("id", "title", "description", "create_time", "last_update_time",
                  "items", "assignments")


class CreateProblemSetSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=128)
    description = serializers.CharField(max_length=1024, allow_blank=True, required=False, default="")


class EditProblemSetSerializer(CreateProblemSetSerializer):
    id = serializers.IntegerField()


class ProblemSetProblemSerializer(serializers.Serializer):
    problem_set = serializers.IntegerField()
    problems = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)


class ProblemSetItemOrderSerializer(serializers.Serializer):
    problem_set = serializers.IntegerField()
    items = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)


class CreateProblemSetAssignmentSerializer(serializers.Serializer):
    problem_set = serializers.IntegerField()
    school_class = serializers.IntegerField()
