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


class CreateSampleSerializer(serializers.Serializer):
    input = serializers.CharField(trim_whitespace=False)
    output = serializers.CharField(trim_whitespace=False)


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
    _id = serializers.CharField(max_length=32, allow_blank=True, allow_null=True)
    title = serializers.CharField(max_length=1024)
    description = serializers.CharField()
    # 입력이 없는 문제("Hello World 출력하기")도 있어 비워둘 수 있다.
    # 교사 출제 화면(TeacherProblemSerializer)도 같은 규칙이다. 여기서만 막으면
    # 교사가 비워 만든 문제를 관리자가 저장할 수 없다(공개 스위치를 켜는 것도 저장이다).
    input_description = serializers.CharField(allow_blank=True)
    output_description = serializers.CharField(allow_blank=True)
    samples = serializers.ListField(child=CreateSampleSerializer(), allow_empty=False)
    test_case_id = serializers.CharField(max_length=32)
    test_case_score = serializers.ListField(child=CreateTestCaseScoreSerializer(), allow_empty=True)
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


class CreateProblemSerializer(CreateOrEditProblemSerializer):
    pass


class EditProblemSerializer(CreateOrEditProblemSerializer):
    id = serializers.IntegerField()


class CreateContestProblemSerializer(CreateOrEditProblemSerializer):
    contest_id = serializers.IntegerField()


class EditContestProblemSerializer(CreateOrEditProblemSerializer):
    id = serializers.IntegerField()
    contest_id = serializers.IntegerField()


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
        exclude = ("test_case_score", "test_case_id", "visible", "is_public",
                   "spj_code", "spj_version", "spj_compile_ok")


class ProblemListSerializer(serializers.ModelSerializer):
    """목록 화면용. 본문·힌트·예제·코드 템플릿은 상세 API 에서 받는다.

    목록에 전문을 실으면 한 페이지에 문제 본문이 10개씩 실려 나간다.
    rule_type 은 화면에 쓰이진 않지만 "내가 푼 문제" 표시(_add_problem_status)에 필요하다.
    """
    tags = serializers.SlugRelatedField(many=True, slug_field="name", read_only=True)

    class Meta:
        model = Problem
        fields = ("id", "_id", "title", "difficulty", "tags", "rule_type", "visibility",
                  "submission_number", "accepted_number")


class ProblemSafeSerializer(BaseProblemSerializer):
    template = serializers.SerializerMethodField("get_public_template")

    class Meta:
        model = Problem
        exclude = ("test_case_score", "test_case_id", "visible", "is_public",
                   "spj_code", "spj_version", "spj_compile_ok",
                   "difficulty", "submission_number", "accepted_number", "statistic_info")


class ContestProblemMakePublicSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    display_id = serializers.CharField(max_length=32)


class ExportProblemSerializer(serializers.ModelSerializer):
    display_id = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    input_description = serializers.SerializerMethodField()
    output_description = serializers.SerializerMethodField()
    test_case_score = serializers.SerializerMethodField()
    hint = serializers.SerializerMethodField()
    spj = serializers.SerializerMethodField()
    template = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()
    tags = serializers.SlugRelatedField(many=True, slug_field="name", read_only=True)

    def get_display_id(self, obj):
        return obj._id

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
    display_id = serializers.CharField()


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
    display_id = serializers.CharField(max_length=128)
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

# 예제는 문제를 여는 모든 학생에게 매번 전송되므로 크기와 개수를 제한한다.
MAX_SAMPLES = 3
MAX_SAMPLE_BYTES = 2 * 1024
# 손으로 넣는 테스트케이스. 많거나 크면 zip 업로드(관리자 화면)를 쓰는 게 맞다.
MAX_CASES = 20
MAX_CASE_BYTES = 64 * 1024


class TeacherTestCaseSerializer(serializers.Serializer):
    input = serializers.CharField(max_length=MAX_CASE_BYTES, allow_blank=True,
                                  trim_whitespace=False)
    output = serializers.CharField(max_length=MAX_CASE_BYTES, allow_blank=True,
                                   trim_whitespace=False)
    # 학생에게 예제로 보여줄지. 체크하지 않은 것은 채점에만 쓰인다.
    is_sample = serializers.BooleanField(default=False)


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
    cases = serializers.ListField(child=TeacherTestCaseSerializer(), allow_empty=False)

    def validate_cases(self, cases):
        if len(cases) > MAX_CASES:
            raise serializers.ValidationError(
                f"테스트 케이스는 {MAX_CASES}개까지 넣을 수 있습니다")
        samples = [c for c in cases if c["is_sample"]]
        if not samples:
            raise serializers.ValidationError("예제로 보여줄 케이스를 하나 이상 골라주세요")
        if len(samples) > MAX_SAMPLES:
            raise serializers.ValidationError(f"예제는 {MAX_SAMPLES}개까지 고를 수 있습니다")
        for case in samples:
            if (len(case["input"].encode("utf-8")) > MAX_SAMPLE_BYTES
                    or len(case["output"].encode("utf-8")) > MAX_SAMPLE_BYTES):
                raise serializers.ValidationError(
                    f"예제로 보여줄 케이스는 {MAX_SAMPLE_BYTES // 1024}KB 를 넘을 수 없습니다")
        return cases


class EditTeacherProblemSerializer(TeacherProblemSerializer):
    id = serializers.IntegerField()
    # 케이스를 다시 보내지 않으면 기존 테스트케이스를 그대로 둔다
    cases = serializers.ListField(child=TeacherTestCaseSerializer(), required=False)


class ReviewProblemPublishSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    approve = serializers.BooleanField()


class TeacherProblemListSerializer(serializers.ModelSerializer):
    """교사가 자기 문제를 관리하는 목록용."""
    tags = serializers.SlugRelatedField(many=True, slug_field="name", read_only=True)

    class Meta:
        model = Problem
        fields = ("id", "_id", "title", "difficulty", "tags", "visibility", "visible",
                  "create_time", "submission_number", "accepted_number")


# ---- 문제집 ----

class ProblemBriefSerializer(serializers.ModelSerializer):
    """문제집 화면용 요약. 본문·테스트케이스는 기존 문제 상세 API 에서 받는다."""
    class Meta:
        model = Problem
        fields = ("id", "_id", "title", "difficulty", "submission_number", "accepted_number")


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
        fields = ("id", "school_class", "class_name", "assigned_at", "due_at", "is_open")

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
    due_at = serializers.DateTimeField(allow_null=True, required=False, default=None)
    is_open = serializers.BooleanField(required=False, default=True)


class EditProblemSetAssignmentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    due_at = serializers.DateTimeField(allow_null=True, required=False)
    is_open = serializers.BooleanField(required=False)
