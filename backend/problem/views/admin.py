import hashlib
import json
import os
import re
import shutil
import zipfile
from wsgiref.util import FileWrapper

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import StreamingHttpResponse, FileResponse

from account.decorators import problem_permission_required, ensure_created_by, super_admin_required, admin_role_required
from contest.models import Contest, ContestStatus
from judge.dispatcher import SPJCompiler
from judge.tasks import rejudge_problem_task, verify_solution_task
from judge.verify import attach_verification, clear_verification, read_verification, \
    spec_from, start_verification
from options.options import SysOptions
from submission.models import Submission, JudgeStatus
from utils.api import APIView, CSRFExemptAPIView, validate_serializer, APIError
from utils.constants import Difficulty
from utils.shortcuts import int_or_none, rand_str, natural_sort_key
from utils.tasks import delete_files
from ..models import (ContestProblem, MAX_CONTEST_PROBLEMS, Problem, ProblemRuleType,
                      ProblemTag, ProblemVisibility)
from ..serializers import (CompileSPJSerializer, MAX_CASE_BYTES,
                           CreateProblemSerializer, EditProblemSerializer,
                           ProblemAdminSerializer, TestCaseUploadForm,
                           AddContestProblemSerializer, ContestProblemAdminSerializer,
                           ExportProblemSerializer,
                           ExportProblemRequestSerialzier, UploadProblemForm, ImportProblemSerializer,
                           TagSerializer, CreateProblemTagSerializer,
                           EditProblemTagSerializer, ReviewProblemPublishSerializer)
from ..utils import (build_problem_template, filter_problem_tags_by_keyword,
                     filter_problems_by_keyword, normalize_tag_aliases)


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
    def read_case_info(self, test_case_id):
        """저장된 테스트케이스의 info 를 목록 형태로 읽어 온다.

        process_zip / process_cases 가 돌려주는 것과 같은 모양이라, 이미 올려둔
        케이스로 문제를 저장할 때 배점을 매기는 데 그대로 쓸 수 있다.
        """
        path = os.path.join(settings.TEST_CASE_DIR, test_case_id, "info")
        try:
            with open(path, encoding="utf-8") as f:
                test_case_info = json.load(f)
        except (IOError, ValueError):
            return []
        cases = test_case_info.get("test_cases", {})
        return [cases[index] for index in sorted(cases, key=int)]

    def read_cases(self, test_case_id, max_bytes=MAX_CASE_BYTES):
        """저장된 테스트케이스를 전부, 담을 수 있는 것은 내용까지 읽어 온다.

        출제 화면이 이것으로 케이스 표를 채운다. 하나만 고치려고 전체를 다시
        타이핑하지 않아도 되고, 예제도 여기서 골라 채운다.

        너무 큰 케이스는 내용 없이 크기만 알린다(too_large). 화면에서 고칠 수
        없으므로, 저장할 때 화면이 {"keep": 번호} 로 돌려보내면 그 파일을 그대로
        옮겨 살린다.
        특수 채점은 정답 파일이 없어 output 이 None 이다(출력은 손으로 받는다).
        """
        test_case_dir = os.path.join(settings.TEST_CASE_DIR, test_case_id)
        try:
            with open(os.path.join(test_case_dir, "info"), encoding="utf-8") as f:
                test_case_info = json.load(f)
        except (IOError, ValueError):
            return []

        spj = test_case_info.get("spj", False)
        cases = []
        # 키는 문자열로 저장된 번호다. 사전 순으로 읽으면 10 이 2 보다 앞선다.
        for index in sorted(test_case_info.get("test_cases", {}), key=int):
            data = test_case_info["test_cases"][index]
            case = {"index": int(index), "input": None, "output": None,
                    "input_size": data.get("input_size", 0),
                    "output_size": data.get("output_size", 0), "too_large": False}
            names = [("input", data.get("input_name"))]
            if not spj:
                names.append(("output", data.get("output_name")))
            for key, name in names:
                path = os.path.join(test_case_dir, name) if name else None
                if not path or not os.path.isfile(path):
                    continue
                if os.path.getsize(path) > max_bytes:
                    case["too_large"] = True
                    continue
                with open(path, "rb") as f:
                    case[key] = f.read().decode("utf-8", errors="replace")
            cases.append(case)
        return cases

    def test_case_digest(self, test_case_id):
        """케이스 묶음의 내용을 나타내는 값.

        저장할 때 예전 것과 견줘 같으면 파일을 갈아끼우지 않는다. 화면에서
        숫자를 지웠다 그대로 다시 써도 "고쳤다" 가 되지 않게 하려는 것이다.
        (화면이 판단하면 그런 것까지 수정으로 세어 재채점이 돈다)
        """
        test_case_dir = os.path.join(settings.TEST_CASE_DIR, test_case_id or "")
        if not os.path.isdir(test_case_dir):
            return None
        digest = hashlib.sha256()
        for name in sorted(os.listdir(test_case_dir)):
            if name == "info":
                continue
            digest.update(name.encode("utf-8"))
            with open(os.path.join(test_case_dir, name), "rb") as f:
                digest.update(f.read())
        return digest.hexdigest()

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

    def process_cases(self, cases, spj=False, previous_test_case_id=None):
        """화면이 보낸 케이스 목록으로 테스트케이스를 다시 만든다.

        zip 업로드와 결과물(파일 이름·info)이 같아야 채점 서버가 그대로 읽는다.
        특수 채점은 정답 파일이 없다. 판정은 spj 코드가 하므로 입력만 쓴다.

        {"keep": 번호} 항목은 화면이 내용을 불러오지 못한 케이스다(너무 크다).
        이전 묶음에서 그 파일을 그대로 옮긴다. 이것이 없으면 큰 케이스가 있는
        문제는 케이스 하나를 고치는 것만으로 나머지가 전부 사라진다.
        """
        previous_dir = (os.path.join(settings.TEST_CASE_DIR, previous_test_case_id)
                        if previous_test_case_id else None)
        previous_info = {}
        if previous_dir:
            try:
                with open(os.path.join(previous_dir, "info"), encoding="utf-8") as f:
                    previous_info = json.load(f).get("test_cases", {})
            except (IOError, ValueError):
                previous_info = {}

        test_case_id = rand_str()
        test_case_dir = os.path.join(settings.TEST_CASE_DIR, test_case_id)
        os.mkdir(test_case_dir)
        os.chmod(test_case_dir, 0o710)

        info = []
        test_case_info = {"spj": spj, "test_cases": {}}
        for index, case in enumerate(cases, start=1):
            kept = previous_info.get(str(case.get("keep"))) if case.get("keep") else None
            if kept:
                data = self._copy_case(previous_dir, test_case_dir, kept, index, spj)
            else:
                data = self._write_case(test_case_dir, case, index, spj)
            info.append(data)
            test_case_info["test_cases"][str(index)] = data

        with open(os.path.join(test_case_dir, "info"), "w", encoding="utf-8") as f:
            f.write(json.dumps(test_case_info, indent=4))
        for item in os.listdir(test_case_dir):
            os.chmod(os.path.join(test_case_dir, item), 0o640)
        return info, test_case_id

    @staticmethod
    def _write_case(test_case_dir, case, index, spj):
        input_name = f"{index}.in"
        # 채점 서버는 줄바꿈을 LF 로 본다(zip 경로와 같게 맞춘다)
        input_bytes = (case.get("input") or "").replace("\r\n", "\n").encode("utf-8")
        with open(os.path.join(test_case_dir, input_name), "wb") as f:
            f.write(input_bytes)
        data = {"input_name": input_name, "input_size": len(input_bytes)}
        if not spj:
            output_name = f"{index}.out"
            output_bytes = (case.get("output") or "").replace("\r\n", "\n").encode("utf-8")
            with open(os.path.join(test_case_dir, output_name), "wb") as f:
                f.write(output_bytes)
            data.update({"output_name": output_name, "output_size": len(output_bytes),
                         "stripped_output_md5": hashlib.md5(output_bytes.rstrip()).hexdigest()})
        return data

    @staticmethod
    def _copy_case(previous_dir, test_case_dir, kept, index, spj):
        """화면이 불러오지 못한 케이스를 이전 묶음에서 그대로 옮긴다."""
        data = {"input_name": f"{index}.in", "input_size": kept.get("input_size", 0)}
        shutil.copyfile(os.path.join(previous_dir, kept["input_name"]),
                        os.path.join(test_case_dir, data["input_name"]))
        if not spj and kept.get("output_name"):
            data.update({"output_name": f"{index}.out",
                         "output_size": kept.get("output_size", 0),
                         "stripped_output_md5": kept.get("stripped_output_md5")})
            shutil.copyfile(os.path.join(previous_dir, kept["output_name"]),
                            os.path.join(test_case_dir, data["output_name"]))
        return data

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

        ensure_created_by(problem, request.user)

        # 예제로 고르라고 케이스 내용만 보여주는 경로. 내려받기와 달리 zip 을 만들지 않는다.
        if request.GET.get("preview") == "1":
            return self.success({"id": problem.test_case_id,
                                 "cases": self.read_cases(problem.test_case_id)})

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
        # 올린 직후 바로 예제를 고를 수 있게 내용까지 함께 준다(교사 경로와 같다)
        return self.success({"id": test_case_id, "info": info, "spj": spj,
                             "cases": self.read_cases(test_case_id)})


class SolutionVerifyAPI(APIView, TestCaseZipProcessor):
    """정답 코드로 테스트케이스가 맞는지 확인한다(교사 화면과 같은 방식).

    저장과 따로 논다. 저장할 때 자동으로 돌지 않고, 통과하지 못해도 저장을
    막지 않는다. 저장하기 전에도 돌릴 수 있다.
    """
    @problem_permission_required
    def post(self, request):
        data = request.data
        if not data.get("solver_code"):
            return self.error("정답 코드를 입력해주세요")
        if not data.get("cases") and not data.get("test_case_id"):
            return self.error("테스트 케이스를 먼저 넣어주세요")
        spec = spec_from(data, time_limit=data.get("time_limit") or 1000,
                         memory_limit=data.get("memory_limit") or 256,
                         io_mode=data.get("io_mode"))
        if spec.get("cases"):
            # {"keep": 번호} 는 내용이 없어 그대로는 채점할 수 없다. 저장 경로와
            # 같은 process_cases 를 태워 이전 묶음에서 옮겨 온다.
            previous = None
            problem = Problem.objects.filter(id=int_or_none(data.get("problem_id"))).first()
            if problem:
                previous = problem.test_case_id
            try:
                _, spec["resolved_test_case_id"] = self.process_cases(
                    spec["cases"], spj=bool(data.get("spj")), previous_test_case_id=previous)
            except (KeyError, IOError, OSError):
                return self.error("테스트 케이스를 읽지 못했습니다. 새로고침 후 다시 시도하세요")
            spec["resolved_is_temporary"] = True
        token = start_verification(spec)
        verify_solution_task.send(token, spec)
        return self.success({"token": token})

    @problem_permission_required
    def get(self, request):
        record = read_verification(request.GET.get("token"))
        if not record:
            return self.error("검증 기록을 찾을 수 없습니다. 다시 눌러주세요")
        return self.success(record)


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
        problems = (Problem.objects.filter(visibility=ProblemVisibility.pending)
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


class ProblemBase(APIView, TestCaseZipProcessor):
    def common_checks(self, request):
        data = request.data
        # 직접 입력한 케이스는 여기서 파일로 만든다. 그 뒤로는 파일로 올린 것과
        # 구분되지 않는다(같은 이름·같은 info 를 쓴다).
        cases = data.pop("cases", None)
        if cases:
            previous = getattr(request, "_previous_test_case_id", None)
            info, new_id = self.process_cases(cases, spj=data["spj"],
                                              previous_test_case_id=previous)
            # 다시 만든 것이 예전과 똑같으면 예전 것을 그대로 쓴다(재채점이 돌지 않게)
            if previous and self.test_case_digest(new_id) == self.test_case_digest(previous):
                delete_files.send(os.path.join(settings.TEST_CASE_DIR, new_id))
                new_id = previous
            data["test_case_id"] = new_id
            # 손으로 넣을 때는 배점을 고르게 나눈다. 케이스마다 다른 점수를 주려면
            # 파일로 올린 뒤 표에서 고쳐야 한다.
            data["test_case_score"] = [
                {"input_name": c["input_name"], "output_name": c.get("output_name", ""),
                 "score": 100 // len(info)} for c in info]
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
        # common_checks 가 cases 를 지우고 test_case_id 로 바꾼다. 지문을 뜰 때
        # 화면이 검증에 보낸 것과 같은 값이 필요해 먼저 챙겨 둔다.
        verified_cases = data.get("cases")
        error_info = self.common_checks(request)
        if error_info:
            return self.error(error_info)

        tags = data.pop("tags")
        tag_objs, error = get_existing_problem_tags(tags)
        if error:
            return self.error(error)
        data["created_by"] = request.user
        token = data.pop("verification_token", None)
        problem = Problem.objects.create(**data)
        problem.tags.set(tag_objs)
        self._attach_verification(problem, token, data, verified_cases)
        return self.success(ProblemAdminSerializer(problem).data)

    @staticmethod
    def _attach_verification(problem, token, data, verified_cases=None):
        """검증해 둔 결과가 지금 저장한 내용의 것이면 붙인다(지문 대조는 서버가 한다).

        지문은 화면이 검증할 때 보낸 것과 같은 값으로 떠야 한다. common_checks 가
        직접 입력한 cases 를 test_case_id 로 바꿔 두므로, 바뀌기 전 값을 받아 쓴다.
        """
        if not token:
            return
        source = dict(data)
        if verified_cases:
            source["cases"] = verified_cases
            source["test_case_id"] = None
        attach_verification(problem, token, spec_from(
            source, time_limit=data["time_limit"], memory_limit=data["memory_limit"],
            io_mode=data.get("io_mode")))

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

        problems = Problem.objects.all().order_by("-create_time")
        if rule_type:
            if rule_type not in ProblemRuleType.choices():
                return self.error("규칙 유형이 올바르지 않습니다")
            else:
                problems = problems.filter(rule_type=rule_type)

        problems = filter_problems_by_keyword(problems, request.GET.get("keyword"))
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

        verified_cases = data.get("cases")
        request._previous_test_case_id = problem.test_case_id
        error_info = self.common_checks(request)
        if error_info:
            return self.error(error_info)
        tags = data.pop("tags")
        token = data.pop("verification_token", None)
        tag_objs, error = get_existing_problem_tags(tags)
        if error:
            return self.error(error)

        # 테스트케이스가 바뀌면 이미 채점된 결과가 실제와 어긋난다. 다시 채점하고
        # 거기서 나온 값(정답률·대회 순위·푼 문제 표시)도 함께 다시 만든다.
        test_cases_changed = data.get("test_case_id") != problem.test_case_id

        for k, v in data.items():
            setattr(problem, k, v)
        problem.save()
        problem.tags.set(tag_objs)

        if test_cases_changed:
            # 지난 검증 결과는 새 케이스에 대한 것이 아니다. 그대로 두면 거짓말이 된다.
            clear_verification(problem.id)
            rejudge_problem_task.send(problem.id)
        self._attach_verification(problem, token, data, verified_cases)
        return self.success({"rejudging": test_cases_changed})

    @problem_permission_required
    def delete(self, request):
        id = request.GET.get("id")
        if not id:
            return self.error("잘못된 요청입니다. id가 필요합니다")
        try:
            problem = Problem.objects.get(id=id)
        except Problem.DoesNotExist:
            return self.error("문제가 존재하지 않습니다")
        ensure_created_by(problem, request.user)
        entry = problem.contest_entries.select_related("contest").first()
        if entry:
            return self.error(f"대회 〈{entry.contest.title}〉에 담긴 문제입니다. "
                              "대회에서 먼저 빼주세요")
        problem.delete()
        return self.success()


class ContestProblemAPI(APIView):
    """대회에 담긴 문제. 문제를 복사하지 않고 관계만 잇는다.

    그래서 "대회 문제 만들기" 가 없다. 문제는 문제 화면에서 만들고(대회 전에는
    비공개로 두면 된다) 여기서는 담고 빼기만 한다.
    """
    @problem_permission_required
    def get(self, request):
        contest_id = int_or_none(request.GET.get("contest_id"))
        if contest_id is None:
            return self.error("잘못된 요청입니다. contest_id가 필요합니다")
        try:
            contest = Contest.objects.get(id=contest_id)
        except Contest.DoesNotExist:
            return self.error("대회가 존재하지 않습니다")
        ensure_created_by(contest, request.user)
        entries = (ContestProblem.objects.filter(contest=contest)
                   .select_related("problem__created_by").prefetch_related("problem__tags"))
        return self.success(self.paginate_data(request, entries, ContestProblemAdminSerializer))

    @problem_permission_required
    @validate_serializer(AddContestProblemSerializer)
    def post(self, request):
        data = request.data
        try:
            contest = Contest.objects.get(id=data["contest_id"])
            problem = Problem.objects.get(id=data["problem_id"])
        except (Contest.DoesNotExist, Problem.DoesNotExist):
            return self.error("대회 또는 문제가 존재하지 않습니다")
        ensure_created_by(contest, request.user)

        if contest.status != ContestStatus.CONTEST_NOT_START:
            return self.error("시작한 대회에는 문제를 넣을 수 없습니다")
        if ContestProblem.objects.filter(contest=contest, problem=problem).exists():
            return self.error("이미 이 대회에 담긴 문제입니다")
        if problem.rule_type != contest.rule_type:
            return self.error("대회와 규칙 유형이 다른 문제입니다")

        order = ContestProblem.next_order(contest)
        if order > MAX_CONTEST_PROBLEMS:
            return self.error(f"대회에는 문제를 {MAX_CONTEST_PROBLEMS}개까지 넣을 수 있습니다")
        try:
            ContestProblem.objects.create(contest=contest, problem=problem, order=order)
        except IntegrityError:
            # 자리를 읽는 것과 저장하는 것 사이에 다른 요청이 같은 자리를 먼저 썼다
            return self.error("문제를 넣지 못했습니다. 다시 시도해주세요")
        return self.success()

    @problem_permission_required
    def delete(self, request):
        """대회에서 문제를 뺀다. 문제 자체는 남는다."""
        contest_id = int_or_none(request.GET.get("contest_id"))
        problem_id = int_or_none(request.GET.get("problem_id"))
        if contest_id is None or problem_id is None:
            return self.error("잘못된 요청입니다. contest_id 와 problem_id 가 필요합니다")
        try:
            contest = Contest.objects.get(id=contest_id)
        except Contest.DoesNotExist:
            return self.error("대회가 존재하지 않습니다")
        ensure_created_by(contest, request.user)
        # 시작한 뒤에 빼면 순위표(submission_info)에 없는 문제 칸이 남는다
        if contest.status != ContestStatus.CONTEST_NOT_START:
            return self.error("시작한 대회에서는 문제를 뺄 수 없습니다")
        ContestProblem.objects.filter(contest=contest, problem_id=problem_id).delete()
        # 가운데를 빼면 라벨이 A, C 로 벌어지므로 다시 붙인다
        ContestProblem.repack(contest)
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
        problems = Problem.objects.filter(id__in=request.data["problem_id"])
        for problem in problems:
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

                        for k, v in problem_info["template"].items():
                            problem_info["template"][k] = build_problem_template(v["prepend"], v["template"],
                                                                                 v["append"])

                        spj = problem_info["spj"] is not None
                        rule_type = problem_info["rule_type"]
                        test_case_score = problem_info["test_case_score"]

                        _, test_case_id = self.process_zip(tmp_file, spj=spj, dir=f"{i}/testcase/")

                        problem_obj = Problem.objects.create(title=problem_info["title"],
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
