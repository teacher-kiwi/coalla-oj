import hashlib
import json
import os
import re
import zipfile
from wsgiref.util import FileWrapper

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import StreamingHttpResponse, FileResponse

from account.decorators import problem_permission_required, ensure_created_by, super_admin_required, admin_role_required
from contest.models import Contest, ContestStatus
from judge.dispatcher import SPJCompiler
from options.options import SysOptions
from submission.models import Submission, JudgeStatus
from utils.api import APIView, CSRFExemptAPIView, validate_serializer, APIError
from utils.constants import Difficulty
from utils.shortcuts import rand_str, natural_sort_key
from utils.tasks import delete_files
from ..models import Problem, ProblemRuleType, ProblemTag, ProblemVisibility
from ..serializers import (CreateContestProblemSerializer, CompileSPJSerializer,
                           CreateProblemSerializer, EditProblemSerializer, EditContestProblemSerializer,
                           ProblemAdminSerializer, TestCaseUploadForm, ContestProblemMakePublicSerializer,
                           AddContestProblemSerializer, ExportProblemSerializer,
                           ExportProblemRequestSerialzier, UploadProblemForm, ImportProblemSerializer,
                           TagSerializer, CreateProblemTagSerializer,
                           EditProblemTagSerializer, ReviewProblemPublishSerializer)
from ..utils import (build_problem_template, filter_problem_tags_by_keyword,
                     normalize_tag_aliases)


# 업로드된 테스트케이스 디렉터리 이름(rand_str 결과). 경로 조작을 막으려고 형태를 확인한다.
TEST_CASE_ID_RE = re.compile(r"^[a-zA-Z0-9]+$")


def check_test_case_score(test_case_id, test_case_score, spj):
    """저장하려는 테스트케이스 정보가 실제 업로드된 파일과 맞는지 확인한다.

    - test_case_id 의 디렉터리가 없으면 채점 서버가 파일을 찾지 못해 그 문제의
      제출이 전부 SYSTEM_ERROR 로 떨어진다.
    - 파일명·개수가 어긋나면 OI 점수 계산이 틀어진다. dispatcher 가 채점 결과와
      test_case_score 를 순서대로 짝지어 점수를 매기기 때문이다.

    둘 다 등록은 성공하고 한참 뒤에야 드러나는 형태라 저장 전에 막는다.
    맞으면 None, 아니면 사유를 돌려준다.
    """
    if not test_case_id or not TEST_CASE_ID_RE.match(test_case_id):
        return "테스트 케이스를 업로드해주세요"
    try:
        with open(os.path.join(settings.TEST_CASE_DIR, test_case_id, "info"), encoding="utf-8") as f:
            cases = list(json.load(f)["test_cases"].values())
    except (OSError, ValueError, KeyError, AttributeError):
        return "테스트 케이스가 존재하지 않습니다. 다시 업로드해주세요"

    if len(cases) != len(test_case_score):
        return f"테스트 케이스 개수가 맞지 않습니다. 업로드된 것은 {len(cases)}개입니다"

    if spj:
        # 특수 채점은 정답 파일 없이 올리므로 입력 파일명만 맞춰본다
        uploaded = {case.get("input_name") for case in cases}
        given = {item["input_name"] for item in test_case_score}
    else:
        if any("output_name" not in case for case in cases):
            return "특수 채점용으로 올린 테스트 케이스입니다. 정답 파일과 함께 다시 업로드해주세요"
        uploaded = {(case["input_name"], case["output_name"]) for case in cases}
        given = {(item["input_name"], item["output_name"]) for item in test_case_score}
    if uploaded != given:
        return "테스트 케이스 파일 이름이 업로드된 것과 다릅니다. 다시 업로드해주세요"


def get_existing_problem_tags(tag_names):
    tag_names = list(dict.fromkeys(tag_names))
    tag_map = {tag.name: tag for tag in ProblemTag.objects.filter(name__in=tag_names)}
    missing = [name for name in tag_names if name not in tag_map]
    if missing:
        return None, "등록되지 않은 태그입니다: " + ", ".join(missing)
    return [tag_map[name] for name in tag_names], None


class ProblemTagAdminAPI(APIView):
    @admin_role_required
    def get(self, request):
        tag_id = request.GET.get("id")
        if tag_id:
            try:
                return self.success(TagSerializer(ProblemTag.objects.get(id=tag_id)).data)
            except ProblemTag.DoesNotExist:
                return self.error("태그가 존재하지 않습니다")

        tags = ProblemTag.objects.order_by("name")
        keyword = request.GET.get("keyword", "").strip()
        if keyword:
            tags = filter_problem_tags_by_keyword(tags, keyword)
        if request.GET.get("paging") == "true":
            return self.success(self.paginate_data(request, tags, TagSerializer))
        return self.success(TagSerializer(tags, many=True).data)

    @validate_serializer(CreateProblemTagSerializer)
    @super_admin_required
    def post(self, request):
        name = request.data["name"].strip()
        aliases = normalize_tag_aliases(request.data.get("aliases", []))
        if not name:
            return self.error("태그 이름을 입력하세요")
        if ProblemTag.objects.filter(name=name).exists():
            return self.error("이미 존재하는 태그입니다")
        try:
            tag = ProblemTag.objects.create(name=name, aliases=aliases)
        except IntegrityError:
            return self.error("이미 존재하는 태그입니다")
        return self.success(TagSerializer(tag).data)

    @validate_serializer(EditProblemTagSerializer)
    @super_admin_required
    def put(self, request):
        data = request.data
        try:
            tag = ProblemTag.objects.get(id=data["id"])
        except ProblemTag.DoesNotExist:
            return self.error("태그가 존재하지 않습니다")
        name = data["name"].strip()
        aliases = normalize_tag_aliases(data.get("aliases", []))
        if not name:
            return self.error("태그 이름을 입력하세요")
        if ProblemTag.objects.exclude(id=tag.id).filter(name=name).exists():
            return self.error("이미 존재하는 태그입니다")
        tag.name = name
        tag.aliases = aliases
        try:
            tag.save(update_fields=["name", "aliases"])
        except IntegrityError:
            return self.error("이미 존재하는 태그입니다")
        return self.success(TagSerializer(tag).data)

    @super_admin_required
    def delete(self, request):
        tag_id = request.GET.get("id")
        if not tag_id:
            return self.error("잘못된 요청입니다. id가 필요합니다")
        try:
            tag = ProblemTag.objects.get(id=tag_id)
        except ProblemTag.DoesNotExist:
            return self.error("태그가 존재하지 않습니다")
        if Problem.objects.filter(tags=tag).exists():
            return self.error("문제에서 사용 중인 태그입니다")
        tag.delete()
        return self.success()


class TestCaseZipProcessor(object):
    def process_zip(self, uploaded_zip_file, spj, dir=""):
        try:
            zip_file = zipfile.ZipFile(uploaded_zip_file, "r")
        except zipfile.BadZipFile:
            raise APIError("올바른 zip 파일이 아닙니다")
        name_list = zip_file.namelist()
        test_case_list = self.filter_name_list(name_list, spj=spj, dir=dir)
        if not test_case_list:
            raise APIError("파일이 비어 있습니다")

        test_case_id = rand_str()
        test_case_dir = os.path.join(settings.TEST_CASE_DIR, test_case_id)
        os.mkdir(test_case_dir)
        os.chmod(test_case_dir, 0o710)

        size_cache = {}
        md5_cache = {}

        for item in test_case_list:
            with open(os.path.join(test_case_dir, item), "wb") as f:
                content = zip_file.read(f"{dir}{item}").replace(b"\r\n", b"\n")
                size_cache[item] = len(content)
                if item.endswith(".out"):
                    md5_cache[item] = hashlib.md5(content.rstrip()).hexdigest()
                f.write(content)
        test_case_info = {"spj": spj, "test_cases": {}}

        info = []

        if spj:
            for index, item in enumerate(test_case_list):
                data = {"input_name": item, "input_size": size_cache[item]}
                info.append(data)
                test_case_info["test_cases"][str(index + 1)] = data
        else:
            # ["1.in", "1.out", "2.in", "2.out"] -> [("1.in", "1.out"), ("2.in", "2.out")]
            test_case_list = zip(*[test_case_list[i::2] for i in range(2)])
            for index, item in enumerate(test_case_list):
                data = {"stripped_output_md5": md5_cache[item[1]],
                        "input_size": size_cache[item[0]],
                        "output_size": size_cache[item[1]],
                        "input_name": item[0],
                        "output_name": item[1]}
                info.append(data)
                test_case_info["test_cases"][str(index + 1)] = data

        with open(os.path.join(test_case_dir, "info"), "w", encoding="utf-8") as f:
            f.write(json.dumps(test_case_info, indent=4))

        for item in os.listdir(test_case_dir):
            os.chmod(os.path.join(test_case_dir, item), 0o640)

        return info, test_case_id

    def process_cases(self, cases):
        """손으로 입력한 입출력 쌍을 테스트케이스로 저장한다.

        zip 업로드와 결과물(파일 이름·info)이 같아야 채점 서버가 그대로 읽는다.
        특수 채점은 정답 파일이 없어야 하므로 이 경로에서는 지원하지 않는다.
        """
        test_case_id = rand_str()
        test_case_dir = os.path.join(settings.TEST_CASE_DIR, test_case_id)
        os.mkdir(test_case_dir)
        os.chmod(test_case_dir, 0o710)

        info = []
        test_case_info = {"spj": False, "test_cases": {}}
        for index, case in enumerate(cases, start=1):
            input_name, output_name = f"{index}.in", f"{index}.out"
            # 채점 서버는 줄바꿈을 LF 로 본다(zip 경로와 같게 맞춘다)
            input_bytes = case["input"].replace("\r\n", "\n").encode("utf-8")
            output_bytes = case["output"].replace("\r\n", "\n").encode("utf-8")
            with open(os.path.join(test_case_dir, input_name), "wb") as f:
                f.write(input_bytes)
            with open(os.path.join(test_case_dir, output_name), "wb") as f:
                f.write(output_bytes)
            data = {"input_name": input_name, "input_size": len(input_bytes),
                    "output_name": output_name, "output_size": len(output_bytes),
                    "stripped_output_md5": hashlib.md5(output_bytes.rstrip()).hexdigest()}
            info.append(data)
            test_case_info["test_cases"][str(index)] = data

        with open(os.path.join(test_case_dir, "info"), "w", encoding="utf-8") as f:
            f.write(json.dumps(test_case_info, indent=4))
        for item in os.listdir(test_case_dir):
            os.chmod(os.path.join(test_case_dir, item), 0o640)
        return info, test_case_id

    def filter_name_list(self, name_list, spj, dir=""):
        ret = []
        prefix = 1
        if spj:
            while True:
                in_name = f"{prefix}.in"
                if f"{dir}{in_name}" in name_list:
                    ret.append(in_name)
                    prefix += 1
                    continue
                else:
                    return sorted(ret, key=natural_sort_key)
        else:
            while True:
                in_name = f"{prefix}.in"
                out_name = f"{prefix}.out"
                if f"{dir}{in_name}" in name_list and f"{dir}{out_name}" in name_list:
                    ret.append(in_name)
                    ret.append(out_name)
                    prefix += 1
                    continue
                else:
                    return sorted(ret, key=natural_sort_key)


class TestCaseAPI(CSRFExemptAPIView, TestCaseZipProcessor):
    request_parsers = ()

    def get(self, request):
        problem_id = request.GET.get("problem_id")
        if not problem_id:
            return self.error("잘못된 요청입니다. problem_id가 필요합니다")
        try:
            problem = Problem.objects.get(id=problem_id)
        except Problem.DoesNotExist:
            return self.error("문제가 존재하지 않습니다")

        if problem.contest:
            ensure_created_by(problem.contest, request.user)
        else:
            ensure_created_by(problem, request.user)

        test_case_dir = os.path.join(settings.TEST_CASE_DIR, problem.test_case_id)
        if not os.path.isdir(test_case_dir):
            return self.error("테스트 케이스가 존재하지 않습니다")
        name_list = self.filter_name_list(os.listdir(test_case_dir), problem.spj)
        name_list.append("info")
        file_name = os.path.join(test_case_dir, problem.test_case_id + ".zip")
        with zipfile.ZipFile(file_name, "w") as file:
            for test_case in name_list:
                file.write(f"{test_case_dir}/{test_case}", test_case)
        response = StreamingHttpResponse(FileWrapper(open(file_name, "rb")),
                                         content_type="application/octet-stream")

        response["Content-Disposition"] = f"attachment; filename=problem_{problem.id}_test_cases.zip"
        response["Content-Length"] = os.path.getsize(file_name)
        return response

    def post(self, request):
        form = TestCaseUploadForm(request.POST, request.FILES)
        if form.is_valid():
            spj = form.cleaned_data["spj"] == "true"
            file = form.cleaned_data["file"]
        else:
            return self.error("업로드에 실패했습니다")
        zip_file = f"/tmp/{rand_str()}.zip"
        with open(zip_file, "wb") as f:
            for chunk in file:
                f.write(chunk)
        info, test_case_id = self.process_zip(zip_file, spj=spj)
        os.remove(zip_file)
        return self.success({"id": test_case_id, "info": info, "spj": spj})


class CompileSPJAPI(APIView):
    @validate_serializer(CompileSPJSerializer)
    def post(self, request):
        data = request.data
        spj_version = rand_str(8)
        error = SPJCompiler(data["spj_code"], spj_version, data["spj_language"]).compile_spj()
        if error:
            return self.error(error)
        else:
            return self.success()


class ProblemPublishReviewAPI(APIView):
    """교사가 공개 신청한 문제를 관리자가 검토한다."""
    @admin_role_required
    def get(self, request):
        problems = (Problem.objects.filter(visibility=ProblemVisibility.pending,
                                           contest_id__isnull=True)
                    .select_related("created_by").prefetch_related("tags"))
        return self.success(ProblemAdminSerializer(problems, many=True).data)

    @validate_serializer(ReviewProblemPublishSerializer)
    @admin_role_required
    def post(self, request):
        problem = Problem.objects.filter(id=request.data["id"],
                                         visibility=ProblemVisibility.pending).first()
        if not problem:
            return self.error("공개 신청 중인 문제가 아닙니다")
        approve = request.data["approve"]
        # 반려하면 다시 비공개로 돌아가고 교사가 고쳐서 다시 신청할 수 있다
        problem.visibility = ProblemVisibility.public if approve else ProblemVisibility.private
        problem.save(update_fields=["visibility"])
        return self.success({"visibility": problem.visibility})


class ProblemBase(APIView):
    def common_checks(self, request):
        data = request.data
        error = check_test_case_score(data["test_case_id"], data["test_case_score"], data["spj"])
        if error:
            return error
        if data["spj"]:
            if not data["spj_language"] or not data["spj_code"]:
                return "특수 채점(SPJ) 설정이 올바르지 않습니다"
            if not data["spj_compile_ok"]:
                return "특수 채점(SPJ) 코드를 먼저 컴파일해야 합니다"
            data["spj_version"] = hashlib.md5(
                (data["spj_language"] + ":" + data["spj_code"]).encode("utf-8")).hexdigest()
        else:
            data["spj_language"] = None
            data["spj_code"] = None
        if data["rule_type"] == ProblemRuleType.OI:
            total_score = 0
            for item in data["test_case_score"]:
                if item["score"] <= 0:
                    return "점수는 1점 이상이어야 합니다"
                else:
                    total_score += item["score"]
            data["total_score"] = total_score
        data["languages"] = list(data["languages"])


class ProblemAPI(ProblemBase):
    @problem_permission_required
    @validate_serializer(CreateProblemSerializer)
    def post(self, request):
        data = request.data
        # 표시 번호는 서버가 매긴다. 직접 넣은 값이 있으면 그것을 쓴다(옛 데이터 이관용).
        _id = data["_id"] or Problem.next_display_id()
        data["_id"] = _id
        if Problem.objects.filter(_id=_id, contest_id__isnull=True).exists():
            return self.error("이미 사용 중인 표시 ID입니다")

        error_info = self.common_checks(request)
        if error_info:
            return self.error(error_info)

        tags = data.pop("tags")
        tag_objs, error = get_existing_problem_tags(tags)
        if error:
            return self.error(error)
        data["created_by"] = request.user
        problem = Problem.objects.create(**data)
        problem.tags.set(tag_objs)
        return self.success(ProblemAdminSerializer(problem).data)

    @problem_permission_required
    def get(self, request):
        problem_id = request.GET.get("id")
        rule_type = request.GET.get("rule_type")
        user = request.user
        if problem_id:
            try:
                problem = Problem.objects.get(id=problem_id)
                ensure_created_by(problem, request.user)
                return self.success(ProblemAdminSerializer(problem).data)
            except Problem.DoesNotExist:
                return self.error("문제가 존재하지 않습니다")

        problems = Problem.objects.filter(contest_id__isnull=True).order_by("-create_time")
        if rule_type:
            if rule_type not in ProblemRuleType.choices():
                return self.error("규칙 유형이 올바르지 않습니다")
            else:
                problems = problems.filter(rule_type=rule_type)

        keyword = request.GET.get("keyword", "").strip()
        if keyword:
            problems = problems.filter(Q(title__icontains=keyword) | Q(_id__icontains=keyword))
        if not user.can_mgmt_all_problem():
            problems = problems.filter(created_by=user)
        return self.success(self.paginate_data(request, problems, ProblemAdminSerializer))

    @problem_permission_required
    @validate_serializer(EditProblemSerializer)
    def put(self, request):
        data = request.data
        problem_id = data.pop("id")

        try:
            problem = Problem.objects.get(id=problem_id)
            ensure_created_by(problem, request.user)
        except Problem.DoesNotExist:
            return self.error("문제가 존재하지 않습니다")

        # 빈 값으로 오면 기존 번호를 유지한다(출제 화면에 번호 칸이 없다)
        _id = data["_id"] or problem._id
        data["_id"] = _id
        if Problem.objects.exclude(id=problem_id).filter(_id=_id, contest_id__isnull=True).exists():
            return self.error("이미 사용 중인 표시 ID입니다")

        error_info = self.common_checks(request)
        if error_info:
            return self.error(error_info)
        tags = data.pop("tags")
        tag_objs, error = get_existing_problem_tags(tags)
        if error:
            return self.error(error)

        for k, v in data.items():
            setattr(problem, k, v)
        problem.save()
        problem.tags.set(tag_objs)

        return self.success()

    @problem_permission_required
    def delete(self, request):
        id = request.GET.get("id")
        if not id:
            return self.error("잘못된 요청입니다. id가 필요합니다")
        try:
            problem = Problem.objects.get(id=id, contest_id__isnull=True)
        except Problem.DoesNotExist:
            return self.error("문제가 존재하지 않습니다")
        ensure_created_by(problem, request.user)
        problem.delete()
        return self.success()


class ContestProblemAPI(ProblemBase):
    @validate_serializer(CreateContestProblemSerializer)
    def post(self, request):
        data = request.data
        try:
            contest = Contest.objects.get(id=data.pop("contest_id"))
            ensure_created_by(contest, request.user)
        except Contest.DoesNotExist:
            return self.error("대회가 존재하지 않습니다")

        if data["rule_type"] != contest.rule_type:
            return self.error("규칙 유형이 올바르지 않습니다")

        _id = data["_id"]
        if not _id:
            return self.error("표시 ID를 입력하세요")

        if Problem.objects.filter(_id=_id, contest=contest).exists():
            return self.error("이미 사용 중인 표시 ID입니다")

        error_info = self.common_checks(request)
        if error_info:
            return self.error(error_info)

        data["contest"] = contest
        tags = data.pop("tags")
        tag_objs, error = get_existing_problem_tags(tags)
        if error:
            return self.error(error)
        data["created_by"] = request.user
        problem = Problem.objects.create(**data)
        problem.tags.set(tag_objs)
        return self.success(ProblemAdminSerializer(problem).data)

    def get(self, request):
        problem_id = request.GET.get("id")
        contest_id = request.GET.get("contest_id")
        user = request.user
        if problem_id:
            try:
                problem = Problem.objects.get(id=problem_id)
                ensure_created_by(problem.contest, user)
            except Problem.DoesNotExist:
                return self.error("문제가 존재하지 않습니다")
            return self.success(ProblemAdminSerializer(problem).data)

        if not contest_id:
            return self.error("잘못된 요청입니다. contest_id가 필요합니다")
        try:
            contest = Contest.objects.get(id=contest_id)
            ensure_created_by(contest, user)
        except Contest.DoesNotExist:
            return self.error("대회가 존재하지 않습니다")
        problems = Problem.objects.filter(contest=contest).order_by("-create_time")
        if user.is_admin():
            problems = problems.filter(contest__created_by=user)
        keyword = request.GET.get("keyword")
        if keyword:
            problems = problems.filter(title__contains=keyword)
        return self.success(self.paginate_data(request, problems, ProblemAdminSerializer))

    @validate_serializer(EditContestProblemSerializer)
    def put(self, request):
        data = request.data
        user = request.user

        try:
            contest = Contest.objects.get(id=data.pop("contest_id"))
            ensure_created_by(contest, user)
        except Contest.DoesNotExist:
            return self.error("대회가 존재하지 않습니다")

        if data["rule_type"] != contest.rule_type:
            return self.error("규칙 유형이 올바르지 않습니다")

        problem_id = data.pop("id")

        try:
            problem = Problem.objects.get(id=problem_id, contest=contest)
        except Problem.DoesNotExist:
            return self.error("문제가 존재하지 않습니다")

        _id = data["_id"]
        if not _id:
            return self.error("표시 ID를 입력하세요")
        if Problem.objects.exclude(id=problem_id).filter(_id=_id, contest=contest).exists():
            return self.error("이미 사용 중인 표시 ID입니다")

        error_info = self.common_checks(request)
        if error_info:
            return self.error(error_info)
        tags = data.pop("tags")
        tag_objs, error = get_existing_problem_tags(tags)
        if error:
            return self.error(error)

        for k, v in data.items():
            setattr(problem, k, v)
        problem.save()
        problem.tags.set(tag_objs)
        return self.success()

    def delete(self, request):
        id = request.GET.get("id")
        if not id:
            return self.error("잘못된 요청입니다. id가 필요합니다")
        try:
            problem = Problem.objects.get(id=id, contest_id__isnull=False)
        except Problem.DoesNotExist:
            return self.error("문제가 존재하지 않습니다")
        ensure_created_by(problem.contest, request.user)
        if Submission.objects.filter(problem=problem).exists():
            return self.error("제출 기록이 있어 문제를 삭제할 수 없습니다")
        problem.delete()
        return self.success()


class MakeContestProblemPublicAPIView(APIView):
    @validate_serializer(ContestProblemMakePublicSerializer)
    @problem_permission_required
    def post(self, request):
        data = request.data
        display_id = data.get("display_id")
        if Problem.objects.filter(_id=display_id, contest_id__isnull=True).exists():
            return self.error("이미 사용 중인 표시 ID입니다")

        try:
            problem = Problem.objects.get(id=data["id"])
        except Problem.DoesNotExist:
            return self.error("문제가 존재하지 않습니다")

        if not problem.contest or problem.is_public:
            return self.error("이미 공개된 문제입니다")
        problem.is_public = True
        problem.save()
        # pk 를 비우고 저장하면 복사본이 만들어진다
        # https://docs.djangoproject.com/en/4.2/topics/db/queries/#copying-model-instances
        tags = problem.tags.all()
        problem.pk = None
        problem.contest = None
        problem._id = display_id
        problem.visible = False
        problem.submission_number = problem.accepted_number = 0
        problem.statistic_info = {}
        problem.save()
        problem.tags.set(tags)
        return self.success()


class AddContestProblemAPI(APIView):
    @validate_serializer(AddContestProblemSerializer)
    def post(self, request):
        data = request.data
        try:
            contest = Contest.objects.get(id=data["contest_id"])
            problem = Problem.objects.get(id=data["problem_id"])
        except (Contest.DoesNotExist, Problem.DoesNotExist):
            return self.error("대회 또는 문제가 존재하지 않습니다")

        if contest.status == ContestStatus.CONTEST_ENDED:
            return self.error("종료된 대회입니다")
        if Problem.objects.filter(contest=contest, _id=data["display_id"]).exists():
            return self.error("이 대회에 이미 같은 표시 ID가 있습니다")

        tags = problem.tags.all()
        problem.pk = None
        problem.contest = contest
        problem.is_public = True
        problem.visible = True
        problem._id = request.data["display_id"]
        problem.submission_number = problem.accepted_number = 0
        problem.statistic_info = {}
        problem.save()
        problem.tags.set(tags)
        return self.success()


class ExportProblemAPI(APIView):
    def choose_answers(self, user, problem):
        ret = []
        for item in problem.languages:
            submission = Submission.objects.filter(problem=problem,
                                                   user_id=user.id,
                                                   language=item,
                                                   result=JudgeStatus.ACCEPTED).order_by("-create_time").first()
            if submission:
                ret.append({"language": submission.language, "code": submission.code})
        return ret

    def process_one_problem(self, zip_file, user, problem, index):
        info = ExportProblemSerializer(problem).data
        info["answers"] = self.choose_answers(user, problem=problem)
        compression = zipfile.ZIP_DEFLATED
        zip_file.writestr(zinfo_or_arcname=f"{index}/problem.json",
                          data=json.dumps(info, indent=4),
                          compress_type=compression)
        problem_test_case_dir = os.path.join(settings.TEST_CASE_DIR, problem.test_case_id)
        with open(os.path.join(problem_test_case_dir, "info")) as f:
            info = json.load(f)
        for k, v in info["test_cases"].items():
            input_name = v["input_name"]
            zip_file.write(filename=os.path.join(problem_test_case_dir, input_name),
                           arcname=f"{index}/testcase/{input_name}",
                           compress_type=compression)
            if not info["spj"]:
                output_name = v["output_name"]
                zip_file.write(filename=os.path.join(problem_test_case_dir, output_name),
                               arcname=f"{index}/testcase/{output_name}",
                               compress_type=compression)

    @validate_serializer(ExportProblemRequestSerialzier)
    def get(self, request):
        problems = Problem.objects.filter(id__in=request.data["problem_id"]).select_related("contest")
        for problem in problems:
            if problem.contest:
                ensure_created_by(problem.contest, request.user)
            else:
                ensure_created_by(problem, request.user)
        path = f"/tmp/{rand_str()}.zip"
        with zipfile.ZipFile(path, "w") as zip_file:
            for index, problem in enumerate(problems):
                self.process_one_problem(zip_file=zip_file, user=request.user, problem=problem, index=index + 1)
        delete_files.send_with_options(args=(path,), delay=300_000)
        resp = FileResponse(open(path, "rb"))
        resp["Content-Type"] = "application/zip"
        resp["Content-Disposition"] = "attachment;filename=problem-export.zip"
        return resp


class ImportProblemAPI(CSRFExemptAPIView, TestCaseZipProcessor):
    request_parsers = ()

    def post(self, request):
        form = UploadProblemForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data["file"]
            tmp_file = f"/tmp/{rand_str()}.zip"
            with open(tmp_file, "wb") as f:
                for chunk in file:
                    f.write(chunk)
        else:
            return self.error("업로드에 실패했습니다")

        count = 0
        with zipfile.ZipFile(tmp_file, "r") as zip_file:
            name_list = zip_file.namelist()
            for item in name_list:
                if "/problem.json" in item:
                    count += 1
            with transaction.atomic():
                for i in range(1, count + 1):
                    with zip_file.open(f"{i}/problem.json") as f:
                        problem_info = json.load(f)
                        serializer = ImportProblemSerializer(data=problem_info)
                        if not serializer.is_valid():
                            return self.error(f"문제 형식이 올바르지 않습니다: {serializer.errors}")
                        else:
                            problem_info = serializer.data
                            for item in problem_info["template"].keys():
                                if item not in SysOptions.language_names:
                                    return self.error(f"지원하지 않는 언어입니다: {item}")
                            tag_objs, error = get_existing_problem_tags(problem_info["tags"])
                            if error:
                                return self.error(error)

                        problem_info["display_id"] = problem_info["display_id"][:24]
                        for k, v in problem_info["template"].items():
                            problem_info["template"][k] = build_problem_template(v["prepend"], v["template"],
                                                                                 v["append"])

                        spj = problem_info["spj"] is not None
                        rule_type = problem_info["rule_type"]
                        test_case_score = problem_info["test_case_score"]

                        _, test_case_id = self.process_zip(tmp_file, spj=spj, dir=f"{i}/testcase/")

                        problem_obj = Problem.objects.create(_id=problem_info["display_id"],
                                                             title=problem_info["title"],
                                                             description=problem_info["description"]["value"],
                                                             input_description=problem_info["input_description"][
                                                                 "value"],
                                                             output_description=problem_info["output_description"][
                                                                 "value"],
                                                             hint=problem_info["hint"]["value"],
                                                             test_case_score=test_case_score if test_case_score else [],
                                                             time_limit=problem_info["time_limit"],
                                                             memory_limit=problem_info["memory_limit"],
                                                             samples=problem_info["samples"],
                                                             template=problem_info["template"],
                                                             rule_type=problem_info["rule_type"],
                                                             source=problem_info["source"],
                                                             spj=spj,
                                                             spj_code=problem_info["spj"]["code"] if spj else None,
                                                             spj_language=problem_info["spj"][
                                                                 "language"] if spj else None,
                                                             spj_version=rand_str(8) if spj else "",
                                                             languages=SysOptions.language_names,
                                                             created_by=request.user,
                                                             visible=False,
                                                             difficulty=Difficulty.L3,
                                                             total_score=sum(item["score"] for item in test_case_score)
                                                             if rule_type == ProblemRuleType.OI else 0,
                                                             test_case_id=test_case_id
                                                             )
                        problem_obj.tags.set(tag_objs)
        return self.success({"import_count": count})
