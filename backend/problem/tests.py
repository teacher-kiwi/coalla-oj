import copy
import hashlib
import json
import os
import shutil
from datetime import timedelta
from zipfile import ZipFile

from django.conf import settings

from utils.api.tests import APITestCase

from .models import ProblemTag, ProblemIOMode
from .models import Problem, ProblemRuleType
from contest.models import Contest
from contest.tests import DEFAULT_CONTEST_DATA

from django.core.management import call_command

from .views.admin import TestCaseAPI
from .utils import filter_problem_tags_by_keyword, parse_problem_template
from utils.management.commands.seed_problem_tags import DEFAULT_TAGS

DEFAULT_PROBLEM_DATA = {"_id": "A-110", "title": "test", "description": "<p>test</p>", "input_description": "test",
                        "output_description": "test", "time_limit": 1000, "memory_limit": 256, "difficulty": "L1",
                        "visible": True, "tags": ["test"], "languages": ["C", "C++", "Java", "Python3"], "template": {},
                        "samples": [{"input": "test", "output": "test"}], "spj": False, "spj_language": "C",
                        "spj_code": "", "spj_compile_ok": True, "test_case_id": "499b26290cc7994e0b497212e842ea85",
                        "test_case_score": [{"output_name": "1.out", "input_name": "1.in", "output_size": 0,
                                             "stripped_output_md5": "d41d8cd98f00b204e9800998ecf8427e",
                                             "input_size": 0, "score": 0}],
                        "io_mode": {"io_mode": ProblemIOMode.standard, "input": "input.txt", "output": "output.txt"},
                        "rule_type": "ACM", "hint": "<p>test</p>", "source": "test"}


def create_test_case_dir(test_case_id=DEFAULT_PROBLEM_DATA["test_case_id"], spj=False):
    """DEFAULT_PROBLEM_DATA 가 가리키는 테스트케이스를 실제로 만들어 둔다.

    문제 저장 API 는 test_case_score 가 업로드된 파일과 맞는지 확인하므로
    (check_test_case_score) 디스크에 info 파일이 있어야 한다.
    """
    test_case_dir = os.path.join(settings.TEST_CASE_DIR, test_case_id)
    os.makedirs(test_case_dir, exist_ok=True)
    case = {"input_name": "1.in", "input_size": 0}
    if not spj:
        case.update({"output_name": "1.out", "output_size": 0,
                     "stripped_output_md5": "d41d8cd98f00b204e9800998ecf8427e"})
    with open(os.path.join(test_case_dir, "info"), "w", encoding="utf-8") as f:
        json.dump({"spj": spj, "test_cases": {"1": case}}, f)
    return test_case_dir


class ProblemCreateTestBase(APITestCase):
    @staticmethod
    def add_problem(problem_data, created_by):
        data = copy.deepcopy(problem_data)
        if data["spj"]:
            if not data["spj_language"] or not data["spj_code"]:
                raise ValueError("Invalid spj")
            data["spj_version"] = hashlib.md5(
                (data["spj_language"] + ":" + data["spj_code"]).encode("utf-8")).hexdigest()
        else:
            data["spj_language"] = None
            data["spj_code"] = None
        if data["rule_type"] == ProblemRuleType.OI:
            total_score = 0
            for item in data["test_case_score"]:
                if item["score"] <= 0:
                    raise ValueError("invalid score")
                else:
                    total_score += item["score"]
            data["total_score"] = total_score
        data["created_by"] = created_by
        tags = data.pop("tags")

        data["languages"] = list(data["languages"])

        problem = Problem.objects.create(**data)

        for item in tags:
            tag = ProblemTag.objects.get(name=item)
            problem.tags.add(tag)
        return problem


class ProblemTagListAPITest(ProblemCreateTestBase):
    def setUp(self):
        self.url = self.reverse("problem_tag_list_api")
        self.admin = self.create_admin(login=False)
        ProblemTag.objects.create(name="쓰이는태그")
        ProblemTag.objects.create(name="안쓰이는태그")

    def test_get_tag_list(self):
        self.assertSuccess(self.client.get(self.url))

    def test_default_hides_tags_without_problems(self):
        # 문제 목록의 태그 사이드바에 고를 수 없는 항목이 늘어나지 않게 한다
        data = copy.deepcopy(DEFAULT_PROBLEM_DATA)
        data["tags"] = ["쓰이는태그"]
        self.add_problem(data, self.admin)

        names = [t["name"] for t in self.client.get(self.url).data["data"]]
        self.assertEqual(names, ["쓰이는태그"])

    def test_all_flag_returns_every_tag(self):
        # 출제 화면은 아직 문제가 없는 태그도 골라야 한다.
        # 이게 빠지면 문제가 0개일 때 태그를 하나도 고를 수 없어 출제 자체가 막힌다.
        names = {t["name"] for t in self.client.get(self.url + "?all=1").data["data"]}
        # 정렬 순서는 DB 콜레이션에 달려 있어 집합으로 비교한다
        self.assertEqual(names, {"쓰이는태그", "안쓰이는태그"})


class SeedProblemTagsTest(APITestCase):
    """기본 태그 시드. 배포할 때마다 실행되므로 여러 번 돌려도 안전해야 한다."""
    def test_creates_default_tags(self):
        call_command("seed_problem_tags")
        self.assertEqual(ProblemTag.objects.count(), len(DEFAULT_TAGS))
        # 교사가 고르는 개념 태그가 들어 있다
        for name in ("입출력", "조건", "반복", "리스트", "문자열"):
            self.assertTrue(ProblemTag.objects.filter(name=name).exists(), name)

    def test_running_twice_changes_nothing(self):
        call_command("seed_problem_tags")
        before = list(ProblemTag.objects.order_by("name").values_list("name", "aliases"))
        call_command("seed_problem_tags")
        after = list(ProblemTag.objects.order_by("name").values_list("name", "aliases"))
        self.assertEqual(before, after)

    def test_fills_missing_aliases_without_dropping_existing(self):
        # 관리자가 손으로 넣은 별칭은 남기고, 기본 별칭만 더한다
        tag = ProblemTag.objects.create(name="반복", aliases=["직접넣은별칭"])
        call_command("seed_problem_tags")
        tag.refresh_from_db()
        self.assertIn("직접넣은별칭", tag.aliases)
        self.assertIn("loop", tag.aliases)

    def test_alias_search_finds_tag_by_block_name(self):
        # 학생 화면의 블록 이름("논리")으로 검색해도 교사 태그("조건")가 걸려야 한다
        call_command("seed_problem_tags")
        found = filter_problem_tags_by_keyword(ProblemTag.objects.all(), "논리")
        self.assertEqual([t.name for t in found], ["조건"])


class TestCaseUploadAPITest(APITestCase):
    def setUp(self):
        self.api = TestCaseAPI()
        self.url = self.reverse("test_case_api")
        self.create_super_admin()

    def test_filter_file_name(self):
        self.assertEqual(self.api.filter_name_list(["1.in", "1.out", "2.in", ".DS_Store"], spj=False),
                         ["1.in", "1.out"])
        self.assertEqual(self.api.filter_name_list(["2.in", "2.out"], spj=False), [])

        self.assertEqual(self.api.filter_name_list(["1.in", "1.out", "2.in"], spj=True), ["1.in", "2.in"])
        self.assertEqual(self.api.filter_name_list(["2.in", "3.in"], spj=True), [])

    def make_test_case_zip(self):
        base_dir = os.path.join("/tmp", "test_case")
        shutil.rmtree(base_dir, ignore_errors=True)
        os.mkdir(base_dir)
        file_names = ["1.in", "1.out", "2.in", ".DS_Store"]
        for item in file_names:
            with open(os.path.join(base_dir, item), "w", encoding="utf-8") as f:
                f.write(item + "\n" + item + "\r\n" + "end")
        zip_file = os.path.join(base_dir, "test_case.zip")
        with ZipFile(os.path.join(base_dir, "test_case.zip"), "w") as f:
            for item in file_names:
                f.write(os.path.join(base_dir, item), item)
        return zip_file

    def test_upload_spj_test_case_zip(self):
        with open(self.make_test_case_zip(), "rb") as f:
            resp = self.client.post(self.url,
                                    data={"spj": "true", "file": f}, format="multipart")
            self.assertSuccess(resp)
            data = resp.data["data"]
            self.assertEqual(data["spj"], True)
            test_case_dir = os.path.join(settings.TEST_CASE_DIR, data["id"])
            self.assertTrue(os.path.exists(test_case_dir))
            for item in data["info"]:
                name = item["input_name"]
                with open(os.path.join(test_case_dir, name), "r", encoding="utf-8") as f:
                    self.assertEqual(f.read(), name + "\n" + name + "\n" + "end")

    def test_upload_test_case_zip(self):
        with open(self.make_test_case_zip(), "rb") as f:
            resp = self.client.post(self.url,
                                    data={"spj": "false", "file": f}, format="multipart")
            self.assertSuccess(resp)
            data = resp.data["data"]
            self.assertEqual(data["spj"], False)
            test_case_dir = os.path.join(settings.TEST_CASE_DIR, data["id"])
            self.assertTrue(os.path.exists(test_case_dir))
            for item in data["info"]:
                name = item["input_name"]
                with open(os.path.join(test_case_dir, name), "r", encoding="utf-8") as f:
                    self.assertEqual(f.read(), name + "\n" + name + "\n" + "end")


class DisplayIdTest(ProblemCreateTestBase):
    """공개 문제의 표시 번호는 서버가 매긴다."""
    def setUp(self):
        self.admin = self.create_admin(login=False)
        ProblemTag.objects.create(name="test")

    def test_first_problem_starts_at_1000(self):
        self.assertEqual(Problem.next_display_id(), "1000")

    def test_next_number_follows_the_largest(self):
        for display_id in ("1000", "1001"):
            data = copy.deepcopy(DEFAULT_PROBLEM_DATA)
            data["_id"] = display_id
            self.add_problem(data, self.admin)
        self.assertEqual(Problem.next_display_id(), "1002")

    def test_letters_are_ignored(self):
        # 대회 문제는 A·B·C 를 쓰므로 숫자만 본다
        data = copy.deepcopy(DEFAULT_PROBLEM_DATA)
        data["_id"] = "A"
        self.add_problem(data, self.admin)
        self.assertEqual(Problem.next_display_id(), "1000")

    def test_problems_are_ordered_by_number_not_text(self):
        for display_id in ("1002", "999", "1000"):
            data = copy.deepcopy(DEFAULT_PROBLEM_DATA)
            data["_id"] = display_id
            self.add_problem(data, self.admin)
        # 문자열 정렬이면 1000, 1002, 999 순서가 된다
        self.assertEqual([p._id for p in Problem.objects.all()], ["999", "1000", "1002"])


class ProblemAdminAPITest(APITestCase):
    def setUp(self):
        self.url = self.reverse("problem_admin_api")
        self.create_super_admin()
        ProblemTag.objects.create(name="test")
        self.data = copy.deepcopy(DEFAULT_PROBLEM_DATA)
        create_test_case_dir()

    def test_create_problem(self):
        resp = self.client.post(self.url, data=self.data)
        self.assertSuccess(resp)
        return resp

    def test_duplicate_display_id(self):
        self.test_create_problem()

        resp = self.client.post(self.url, data=self.data)
        self.assertFailed(resp, "이미 사용 중인 표시 ID입니다")

    def test_spj(self):
        data = copy.deepcopy(self.data)
        data["spj"] = True

        resp = self.client.post(self.url, data)
        self.assertFailed(resp, "특수 채점(SPJ) 설정이 올바르지 않습니다")

        data["spj_code"] = "test"
        resp = self.client.post(self.url, data=data)
        self.assertSuccess(resp)

    def test_reject_unknown_test_case(self):
        data = copy.deepcopy(self.data)
        data["test_case_id"] = "0" * 32
        self.assertFailed(self.client.post(self.url, data=data),
                          "테스트 케이스가 존재하지 않습니다. 다시 업로드해주세요")

    def test_reject_test_case_name_mismatch(self):
        data = copy.deepcopy(self.data)
        data["test_case_score"][0]["input_name"] = "2.in"
        self.assertFailed(self.client.post(self.url, data=data),
                          "테스트 케이스 파일 이름이 업로드된 것과 다릅니다. 다시 업로드해주세요")

    def test_reject_test_case_count_mismatch(self):
        data = copy.deepcopy(self.data)
        data["test_case_score"].append(copy.deepcopy(data["test_case_score"][0]))
        data["test_case_score"][1]["input_name"] = "2.in"
        data["test_case_score"][1]["output_name"] = "2.out"
        self.assertFailed(self.client.post(self.url, data=data),
                          "테스트 케이스 개수가 맞지 않습니다. 업로드된 것은 1개입니다")

    def test_reject_spj_test_case_for_normal_problem(self):
        create_test_case_dir(spj=True)
        self.assertFailed(self.client.post(self.url, data=self.data),
                          "특수 채점용으로 올린 테스트 케이스입니다. 정답 파일과 함께 다시 업로드해주세요")

    def test_get_problem(self):
        self.test_create_problem()
        resp = self.client.get(self.url)
        self.assertSuccess(resp)

    def test_get_one_problem(self):
        problem_id = self.test_create_problem().data["data"]["id"]
        resp = self.client.get(self.url + "?id=" + str(problem_id))
        self.assertSuccess(resp)

    def test_edit_problem(self):
        problem_id = self.test_create_problem().data["data"]["id"]
        data = copy.deepcopy(self.data)
        data["id"] = problem_id
        resp = self.client.put(self.url, data=data)
        self.assertSuccess(resp)

    def test_create_problem_with_unknown_tag(self):
        data = copy.deepcopy(self.data)
        data["tags"] = ["unknown"]
        resp = self.client.post(self.url, data=data)
        self.assertFailed(resp, "등록되지 않은 태그입니다: unknown")
        self.assertFalse(ProblemTag.objects.filter(name="unknown").exists())


class ProblemTagAdminAPITest(APITestCase):
    def setUp(self):
        self.url = self.reverse("problem_tag_admin_api")
        self.create_super_admin()

    def test_create_tag(self):
        resp = self.client.post(self.url, data={"name": "math", "aliases": ["math", " math "]})
        self.assertSuccess(resp)
        tag = ProblemTag.objects.get(name="math")
        self.assertEqual(tag.aliases, ["math"])

    def test_get_tag_by_alias_keyword(self):
        ProblemTag.objects.update_or_create(name="동적계획법",
                                            defaults={"aliases": ["dp", "dynamic_programming"]})
        resp = self.client.get(self.url, data={"keyword": "dynamic programming"})
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"][0]["name"], "동적계획법")

    def test_duplicate_tag(self):
        ProblemTag.objects.create(name="math")
        resp = self.client.post(self.url, data={"name": "math"})
        self.assertFailed(resp, "이미 존재하는 태그입니다")

    def test_delete_used_tag(self):
        ProblemTag.objects.create(name="test")
        problem = ProblemCreateTestBase.add_problem(DEFAULT_PROBLEM_DATA, self.create_admin(login=False))
        resp = self.client.delete(self.url + "?id=" + str(problem.tags.first().id))
        self.assertFailed(resp, "문제에서 사용 중인 태그입니다")


class ProblemAPITest(ProblemCreateTestBase):
    def setUp(self):
        self.url = self.reverse("problem_api")
        admin = self.create_admin(login=False)
        ProblemTag.objects.create(name="test")
        self.problem = self.add_problem(DEFAULT_PROBLEM_DATA, admin)
        self.create_user("test", "test123")

    def test_get_problem_list(self):
        resp = self.client.get(f"{self.url}?limit=10")
        self.assertSuccess(resp)

    def get_one_problem(self):
        resp = self.client.get(self.url + "?id=" + self.problem._id)
        self.assertSuccess(resp)


class ContestProblemAdminTest(APITestCase):
    def setUp(self):
        self.url = self.reverse("contest_problem_admin_api")
        self.create_admin()
        ProblemTag.objects.create(name="test")
        create_test_case_dir()
        self.contest = self.client.post(self.reverse("contest_admin_api"), data=DEFAULT_CONTEST_DATA).data["data"]

    def test_create_contest_problem(self):
        data = copy.deepcopy(DEFAULT_PROBLEM_DATA)
        data["contest_id"] = self.contest["id"]
        resp = self.client.post(self.url, data=data)
        self.assertSuccess(resp)
        return resp.data["data"]

    def test_get_contest_problem(self):
        self.test_create_contest_problem()
        contest_id = self.contest["id"]
        resp = self.client.get(self.url + "?contest_id=" + str(contest_id))
        self.assertSuccess(resp)
        self.assertEqual(len(resp.data["data"]["results"]), 1)

    def test_get_one_contest_problem(self):
        contest_problem = self.test_create_contest_problem()
        contest_id = self.contest["id"]
        problem_id = contest_problem["id"]
        resp = self.client.get(f"{self.url}?contest_id={contest_id}&id={problem_id}")
        self.assertSuccess(resp)


class ContestProblemTest(ProblemCreateTestBase):
    def setUp(self):
        admin = self.create_admin()
        ProblemTag.objects.create(name="test")
        url = self.reverse("contest_admin_api")
        contest_data = copy.deepcopy(DEFAULT_CONTEST_DATA)
        contest_data["password"] = ""
        contest_data["start_time"] = contest_data["start_time"] + timedelta(hours=1)
        self.contest = self.client.post(url, data=contest_data).data["data"]
        self.problem = self.add_problem(DEFAULT_PROBLEM_DATA, admin)
        self.problem.contest_id = self.contest["id"]
        self.problem.save()
        self.url = self.reverse("contest_problem_api")

    def test_admin_get_contest_problem_list(self):
        contest_id = self.contest["id"]
        resp = self.client.get(self.url + "?contest_id=" + str(contest_id))
        self.assertSuccess(resp)
        self.assertEqual(len(resp.data["data"]), 1)

    def test_admin_get_one_contest_problem(self):
        contest_id = self.contest["id"]
        problem_id = self.problem._id
        resp = self.client.get("{}?contest_id={}&problem_id={}".format(self.url, contest_id, problem_id))
        self.assertSuccess(resp)

    def test_regular_user_get_not_started_contest_problem(self):
        self.create_user("test", "test123")
        resp = self.client.get(self.url + "?contest_id=" + str(self.contest["id"]))
        self.assertDictEqual(resp.data, {"error": "error", "data": "아직 시작하지 않은 대회입니다."})

    def test_reguar_user_get_started_contest_problem(self):
        self.create_user("test", "test123")
        contest = Contest.objects.first()
        contest.start_time = contest.start_time - timedelta(hours=1)
        contest.save()
        resp = self.client.get(self.url + "?contest_id=" + str(self.contest["id"]))
        self.assertSuccess(resp)


class AddProblemFromPublicProblemAPITest(ProblemCreateTestBase):
    def setUp(self):
        admin = self.create_admin()
        ProblemTag.objects.create(name="test")
        url = self.reverse("contest_admin_api")
        contest_data = copy.deepcopy(DEFAULT_CONTEST_DATA)
        contest_data["password"] = ""
        contest_data["start_time"] = contest_data["start_time"] + timedelta(hours=1)
        self.contest = self.client.post(url, data=contest_data).data["data"]
        self.problem = self.add_problem(DEFAULT_PROBLEM_DATA, admin)
        self.url = self.reverse("add_contest_problem_from_public_api")
        self.data = {
            "display_id": "1000",
            "contest_id": self.contest["id"],
            "problem_id": self.problem.id
        }

    def test_add_contest_problem(self):
        resp = self.client.post(self.url, data=self.data)
        self.assertSuccess(resp)
        self.assertTrue(Problem.objects.all().exists())
        self.assertTrue(Problem.objects.filter(contest_id=self.contest["id"]).exists())


class ParseProblemTemplateTest(APITestCase):
    def test_parse(self):
        template_str = """
//PREPEND BEGIN
aaa
//PREPEND END

//TEMPLATE BEGIN
bbb
//TEMPLATE END

//APPEND BEGIN
ccc
//APPEND END
"""

        ret = parse_problem_template(template_str)
        self.assertEqual(ret["prepend"], "aaa\n")
        self.assertEqual(ret["template"], "bbb\n")
        self.assertEqual(ret["append"], "ccc\n")

    def test_parse1(self):
        template_str = """
//PREPEND BEGIN
aaa
//PREPEND END

//APPEND BEGIN
ccc
//APPEND END
//APPEND BEGIN
ddd
//APPEND END
"""

        ret = parse_problem_template(template_str)
        self.assertEqual(ret["prepend"], "aaa\n")
        self.assertEqual(ret["template"], "")
        self.assertEqual(ret["append"], "ccc\n")
