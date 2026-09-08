import copy
import hashlib
import json
import os
import shutil
from datetime import timedelta
from unittest import mock
from zipfile import ZipFile

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils.timezone import now

from judge.dispatcher import JudgeDispatcher
from submission.models import JudgeStatus, Submission
from utils.api.tests import APITestCase
from utils.shortcuts import rand_str

from .models import ProblemFavorite, ProblemTag, ProblemIOMode
from .serializers import MAX_SAMPLE_BYTES
from .views.admin import TestCaseZipProcessor
from .models import (contest_problem_label, contest_problem_order, ContestProblem,
                     Problem, ProblemRuleType)
from contest.models import Contest
from contest.tests import DEFAULT_CONTEST_DATA

from django.core.management import call_command

from .views.admin import TestCaseAPI
from .utils import filter_problem_tags_by_keyword, parse_problem_template
from utils.management.commands.seed_problem_tags import DEFAULT_TAGS

DEFAULT_PROBLEM_DATA = {"title": "test", "description": "<p>test</p>", "input_description": "test",
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

    def test_upload_returns_cases_to_pick_samples_from(self):
        """올린 직후 예제를 고를 수 있어야 한다. 내용이 없으면 화면이 고를 것이 없다."""
        with open(self.make_test_case_zip(), "rb") as f:
            resp = self.client.post(self.url,
                                    data={"spj": "false", "file": f}, format="multipart")
        self.assertSuccess(resp)
        cases = resp.data["data"]["cases"]
        self.assertEqual([c["index"] for c in cases], [1])
        self.assertEqual(cases[0]["input"], "1.in\n1.in\nend")
        self.assertEqual(cases[0]["output"], "1.out\n1.out\nend")

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
    """공개 문제의 번호는 pk 다."""
    def setUp(self):
        self.admin = self.create_admin(login=False)
        ProblemTag.objects.create(name="test")

    def _add(self):
        return self.add_problem(copy.deepcopy(DEFAULT_PROBLEM_DATA), self.admin)

    def test_number_is_the_primary_key(self):
        problem = self._add()
        self.assertEqual(problem.display_id, str(problem.id))

    def test_numbers_do_not_repeat(self):
        numbers = [self._add().display_id for _ in range(3)]
        self.assertEqual(len(set(numbers)), 3)

    def test_problems_are_ordered_by_number(self):
        for _ in range(3):
            self._add()
        numbers = [p.id for p in Problem.objects.all()]
        self.assertEqual(numbers, sorted(numbers))


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
        resp = self.client.get(self.url + "?id=" + str(self.problem.id))
        self.assertSuccess(resp)


class AdminManualCasesTest(ProblemCreateTestBase):
    """관리자도 케이스를 손으로 넣을 수 있다. 교사 화면과 같은 길이다."""
    def setUp(self):
        self.url = self.reverse("problem_admin_api")
        self.create_super_admin()
        ProblemTag.objects.create(name="test")

    def _create(self, **overrides):
        data = copy.deepcopy(DEFAULT_PROBLEM_DATA)
        data.pop("test_case_id")
        data.pop("test_case_score")
        data["cases"] = [{"input": "1 2", "output": "3"}, {"input": "4 5", "output": "9"}]
        data.update(overrides)
        return self.client.post(self.url, data=data)

    def test_cases_become_test_case_files(self):
        resp = self._create()
        self.assertSuccess(resp)
        problem = Problem.objects.get(id=resp.data["data"]["id"])
        test_case_dir = os.path.join(settings.TEST_CASE_DIR, problem.test_case_id)
        self.addCleanup(shutil.rmtree, test_case_dir, ignore_errors=True)
        with open(os.path.join(test_case_dir, "2.out")) as f:
            self.assertEqual(f.read(), "9")
        self.assertEqual(len(problem.test_case_score), 2)

    def test_cannot_use_both_input_methods(self):
        data = copy.deepcopy(DEFAULT_PROBLEM_DATA)
        data["cases"] = [{"input": "1", "output": "1"}]
        self.assertFailed(self.client.post(self.url, data=data),
                          "테스트 케이스는 직접 입력과 파일 중 하나로만 넣을 수 있습니다")

    def test_one_of_them_is_required(self):
        data = copy.deepcopy(DEFAULT_PROBLEM_DATA)
        data.pop("test_case_id")
        data.pop("test_case_score")
        self.assertFailed(self.client.post(self.url, data=data), "테스트 케이스를 넣어주세요")


class ReadCasesTest(APITestCase):
    """저장된 테스트케이스를 되읽어 예제로 고를 수 있게 보여주는 부분.

    예제를 손으로 따로 치면 실제 채점 데이터와 어긋날 수 있다. 여기서 고르면
    그럴 수 없다는 것이 이 기능의 요점이다.
    """
    def setUp(self):
        self.processor = TestCaseZipProcessor()
        self.test_case_id = rand_str()
        self.dir = os.path.join(settings.TEST_CASE_DIR, self.test_case_id)
        os.makedirs(self.dir)
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def _write(self, cases, spj=False):
        info = {"spj": spj, "test_cases": {}}
        for index, (text_in, text_out) in enumerate(cases, start=1):
            data = {"input_name": f"{index}.in", "input_size": len(text_in)}
            with open(os.path.join(self.dir, f"{index}.in"), "w", encoding="utf-8") as f:
                f.write(text_in)
            if not spj:
                data.update({"output_name": f"{index}.out", "output_size": len(text_out)})
                with open(os.path.join(self.dir, f"{index}.out"), "w", encoding="utf-8") as f:
                    f.write(text_out)
            info["test_cases"][str(index)] = data
        with open(os.path.join(self.dir, "info"), "w", encoding="utf-8") as f:
            json.dump(info, f)

    def test_reads_input_and_output(self):
        self._write([("1 2", "3"), ("4 5", "9")])
        cases = self.processor.read_cases(self.test_case_id)
        self.assertEqual([(c["index"], c["input"], c["output"]) for c in cases],
                         [(1, "1 2", "3"), (2, "4 5", "9")])
        self.assertFalse(any(c["too_large"] for c in cases))

    def test_only_the_first_few(self):
        self._write([(str(i), str(i)) for i in range(10)])
        cases = self.processor.read_cases(self.test_case_id)
        self.assertEqual([c["index"] for c in cases], [1, 2, 3, 4, 5])

    def test_numbers_are_sorted_as_numbers(self):
        """키가 문자열이라 사전 순으로 읽으면 10 이 2 보다 앞선다"""
        self._write([(str(i), str(i)) for i in range(12)])
        cases = self.processor.read_cases(self.test_case_id, limit=12)
        self.assertEqual([c["index"] for c in cases], list(range(1, 13)))

    def test_large_case_is_flagged_not_returned(self):
        """예제는 문제 화면에 그대로 나온다. 크면 학생 화면이 망가진다."""
        self._write([("x" * (MAX_SAMPLE_BYTES + 1), "y")])
        case = self.processor.read_cases(self.test_case_id)[0]
        self.assertTrue(case["too_large"])
        self.assertIsNone(case["input"])
        self.assertEqual(case["output"], "y")

    def test_spj_has_no_output(self):
        """특수 채점은 정답 파일이 없다. 예제 출력은 손으로 받아야 한다."""
        self._write([("1 2", "")], spj=True)
        case = self.processor.read_cases(self.test_case_id)[0]
        self.assertEqual(case["input"], "1 2")
        self.assertIsNone(case["output"])

    def test_missing_test_case_is_not_an_error(self):
        self.assertEqual(self.processor.read_cases("없는아이디"), [])


class ProblemFavoriteAPITest(ProblemCreateTestBase):
    """즐겨찾기. 푼 문제 표시와 달리 사용자가 직접 켜고 끄는 값이다."""
    def setUp(self):
        self.url = self.reverse("problem_api")
        self.favorite_url = self.reverse("problem_favorite_api")
        admin = self.create_admin(login=False)
        ProblemTag.objects.create(name="test")
        self.problem = self.add_problem(DEFAULT_PROBLEM_DATA, admin)
        other = copy.deepcopy(DEFAULT_PROBLEM_DATA)
        other["title"] = "다른 문제"
        self.other = self.add_problem(other, admin)
        self.user = self.create_user("test", "test123")

    def _add(self, problem_id=None):
        return self.client.post(self.favorite_url,
                                data={"problem_id": problem_id or self.problem.id})

    def _list(self, favorite=False):
        query = "&favorite=1" if favorite else ""
        resp = self.client.get(f"{self.url}?limit=10{query}")
        self.assertSuccess(resp)
        return resp.data["data"]["results"]

    def test_add_and_remove(self):
        self.assertSuccess(self._add())
        self.assertTrue(ProblemFavorite.objects.filter(user=self.user,
                                                       problem=self.problem).exists())
        self.assertSuccess(self.client.delete(
            f"{self.favorite_url}?problem_id={self.problem.id}"))
        self.assertEqual(ProblemFavorite.objects.count(), 0)

    def test_add_twice_is_fine(self):
        """하트를 두 번 눌러도(느린 응답에 두 번 클릭) 오류가 아니다"""
        self.assertSuccess(self._add())
        self.assertSuccess(self._add())
        self.assertEqual(ProblemFavorite.objects.count(), 1)

    def test_list_marks_my_favorite(self):
        self._add()
        by_id = {p["id"]: p["my_favorite"] for p in self._list()}
        self.assertTrue(by_id[self.problem.id])
        self.assertFalse(by_id[self.other.id])

    def test_detail_marks_my_favorite(self):
        self._add()
        resp = self.client.get(f"{self.url}?problem_id={self.problem.id}")
        self.assertSuccess(resp)
        self.assertTrue(resp.data["data"]["my_favorite"])

    def test_filter_shows_only_favorites(self):
        self._add()
        self.assertEqual([p["id"] for p in self._list(favorite=True)], [self.problem.id])

    def test_anonymous_cannot_favorite(self):
        self.client.logout()
        self.assertFailed(self._add())
        self.assertEqual(ProblemFavorite.objects.count(), 0)

    def test_anonymous_favorite_filter_is_empty(self):
        """로그인하지 않으면 담아둔 것이 없다. 필터가 무시되면 전체가 나온다."""
        self.client.logout()
        self.assertEqual(self._list(favorite=True), [])
        self.assertEqual(len(self._list()), 2)

    def test_unknown_problem_rejected(self):
        self.assertFailed(self._add(self.problem.id + 1000), "문제가 존재하지 않습니다")
        self.assertFailed(self._add("abc"), "문제가 존재하지 않습니다")

    def test_filter_ignores_other_users_favorites(self):
        """남이 담아둔 것이 내 목록에 섞이면 안 된다"""
        self._add()
        self.client.logout()
        other = self.create_user("test2", "test123")
        ProblemFavorite.objects.create(user=other, problem=self.other)
        self.assertEqual([p["id"] for p in self._list(favorite=True)], [self.other.id])

    def test_deleting_problem_removes_favorite(self):
        self._add()
        self.problem.delete()
        self.assertEqual(ProblemFavorite.objects.count(), 0)


class PublicProblemLookupTest(ProblemCreateTestBase):
    """공개 문제는 번호(pk)로 연다. 주소에는 아무 값이나 들어온다."""
    def setUp(self):
        self.url = self.reverse("problem_api")
        admin = self.create_admin(login=False)
        ProblemTag.objects.create(name="test")
        self.problem = self.add_problem(DEFAULT_PROBLEM_DATA, admin)

    def _get(self, problem_id):
        return self.client.get(f"{self.url}?problem_id={problem_id}")

    def test_open_by_number(self):
        resp = self._get(self.problem.id)
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["display_id"], str(self.problem.id))

    def test_unreadable_number_is_not_an_error(self):
        # 번호가 정수 컬럼을 넘거나 숫자가 아니면 DB 에 넘기기 전에 걸러야 한다.
        # 그대로 넘기면 500 이 난다.
        # 빈 값은 목록 요청이라 여기서 보지 않는다
        for value in ("abc", "-1", "0", "99999999999999999999", "1.5"):
            self.assertFailed(self._get(value), "문제가 존재하지 않습니다")

    def test_missing_number_is_not_an_error(self):
        self.assertFailed(self._get(self.problem.id + 1000), "문제가 존재하지 않습니다")


class ProblemKeywordSearchTest(ProblemCreateTestBase):
    """목록 검색. 번호가 pk 라 부분 일치는 뜻이 없어 정확히 그 번호만 본다."""
    def setUp(self):
        self.url = self.reverse("problem_api")
        admin = self.create_admin(login=False)
        ProblemTag.objects.create(name="test")
        data = copy.deepcopy(DEFAULT_PROBLEM_DATA)
        data["title"] = "거북이 그리기"
        self.problem = self.add_problem(data, admin)
        data["title"] = "다른 문제"
        self.other = self.add_problem(data, admin)

    def _search(self, keyword):
        resp = self.client.get(f"{self.url}?limit=10&keyword={keyword}")
        self.assertSuccess(resp)
        return [p["display_id"] for p in resp.data["data"]["results"]]

    def test_search_by_title(self):
        self.assertEqual(self._search("거북이"), [str(self.problem.id)])

    def test_search_by_number(self):
        self.assertEqual(self._search(self.problem.id), [str(self.problem.id)])

    def test_number_too_big_is_not_an_error(self):
        # 정수 컬럼 범위를 넘는 값을 그대로 넘기면 DB 가 거절해 500 이 난다
        self.assertEqual(self._search("99999999999999999999"), [])


class RejudgeOnTestCaseChangeTest(APITestCase):
    """테스트케이스를 갈아끼우면 다시 채점한다. 그러지 않으면 옛 결과가 남는다."""
    def setUp(self):
        self.create_super_admin()
        ProblemTag.objects.create(name="test")
        create_test_case_dir()
        self.url = self.reverse("problem_admin_api")
        self.problem = self.client.post(self.url, data=copy.deepcopy(DEFAULT_PROBLEM_DATA)).data["data"]

    def _edit(self, **changes):
        data = copy.deepcopy(DEFAULT_PROBLEM_DATA)
        data["id"] = self.problem["id"]
        data.update(changes)
        with mock.patch("problem.views.admin.rejudge_problem_task.send") as send:
            resp = self.client.put(self.url, data=data)
        self.assertSuccess(resp)
        return resp.data["data"], send

    def test_new_test_cases_start_a_rejudge(self):
        # 테스트케이스 디렉터리는 테스트끼리 공유하므로 쓰고 나서 치운다
        new_id = rand_str()
        create_test_case_dir(new_id)
        self.addCleanup(shutil.rmtree,
                        os.path.join(settings.TEST_CASE_DIR, new_id), ignore_errors=True)
        data, send = self._edit(test_case_id=new_id)
        send.assert_called_once_with(self.problem["id"])
        self.assertTrue(data["rejudging"])

    def test_editing_something_else_does_not(self):
        """제목만 고쳤는데 전부 다시 채점하면 대회 중에 채점 서버가 멈춘다."""
        data, send = self._edit(title="제목만 고침")
        send.assert_not_called()
        self.assertFalse(data["rejudging"])


class TestCaseDownloadTest(ProblemCreateTestBase):
    """테스트케이스 내려받기. 대회에 담긴 문제도 그냥 문제다."""
    def setUp(self):
        self.admin = self.create_super_admin()
        ProblemTag.objects.create(name="test")
        create_test_case_dir()
        self.problem = self.add_problem(DEFAULT_PROBLEM_DATA, self.admin)
        self.url = self.reverse("test_case_api")

    def test_download(self):
        resp = self.client.get(self.url + f"?problem_id={self.problem.id}")
        self.assertEqual(resp.status_code, 200)

    def test_download_a_problem_that_is_in_a_contest(self):
        contest = Contest.objects.create(
            title="c", description="d", rule_type="ACM", real_time_rank=True,
            start_time=now(), end_time=now() + timedelta(days=1), created_by=self.admin)
        ContestProblem.objects.create(contest=contest, problem=self.problem, order=1)
        resp = self.client.get(self.url + f"?problem_id={self.problem.id}")
        self.assertEqual(resp.status_code, 200)


class ContestProblemAdminTest(ProblemCreateTestBase):
    """대회 문제는 만들지 않고 담고 뺀다. 문제를 복사하지 않는다."""
    def setUp(self):
        self.url = self.reverse("contest_problem_admin_api")
        self.admin = self.create_admin()
        ProblemTag.objects.create(name="test")
        create_test_case_dir()
        contest_data = copy.deepcopy(DEFAULT_CONTEST_DATA)
        contest_data["start_time"] = str(now() + timedelta(hours=1))
        contest_data["end_time"] = str(now() + timedelta(hours=2))
        self.contest = self.client.post(self.reverse("contest_admin_api"),
                                        data=contest_data).data["data"]
        self.problem = self.add_problem(DEFAULT_PROBLEM_DATA, self.admin)

    def _add(self, problem=None):
        return self.client.post(self.url, data={"contest_id": self.contest["id"],
                                                "problem_id": (problem or self.problem).id})

    def test_add_problem(self):
        self.assertSuccess(self._add())
        entry = ContestProblem.objects.get(contest_id=self.contest["id"])
        self.assertEqual(entry.problem_id, self.problem.id)
        self.assertEqual(entry.label, "A")
        # 문제는 복사되지 않는다
        self.assertEqual(Problem.objects.count(), 1)

    def test_same_problem_cannot_be_added_twice(self):
        self.assertSuccess(self._add())
        self.assertFailed(self._add(), "이미 이 대회에 담긴 문제입니다")

    def test_list_shows_the_contest_label(self):
        self.assertSuccess(self._add())
        resp = self.client.get(self.url + "?contest_id=" + str(self.contest["id"]))
        self.assertSuccess(resp)
        results = resp.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["display_id"], "A")

    def test_remove_keeps_the_problem(self):
        self.assertSuccess(self._add())
        contest_id = self.contest["id"]
        self.assertSuccess(self.client.delete(
            f"{self.url}?contest_id={contest_id}&problem_id={self.problem.id}"))
        self.assertFalse(ContestProblem.objects.exists())
        self.assertTrue(Problem.objects.filter(id=self.problem.id).exists())

    def test_labels_are_repacked_after_removal(self):
        """가운데를 빼면 A, C 로 벌어진다. 시작 전이라 번호를 다시 붙여도 안전하다."""
        problems = [self.problem] + [self.add_problem(DEFAULT_PROBLEM_DATA, self.admin)
                                     for _ in range(2)]
        for problem in problems:
            self.assertSuccess(self._add(problem))
        contest_id = self.contest["id"]
        self.assertSuccess(self.client.delete(
            f"{self.url}?contest_id={contest_id}&problem_id={problems[1].id}"))

        entries = ContestProblem.objects.filter(contest_id=contest_id).order_by("order")
        self.assertEqual([e.label for e in entries], ["A", "B"])
        self.assertEqual([e.problem_id for e in entries], [problems[0].id, problems[2].id])

    def test_rule_type_must_match_the_contest(self):
        data = copy.deepcopy(DEFAULT_PROBLEM_DATA)
        data["rule_type"] = ProblemRuleType.OI
        # OI 는 테스트케이스마다 점수가 있어야 한다
        data["test_case_score"] = [dict(item, score=100) for item in data["test_case_score"]]
        oi_problem = self.add_problem(data, self.admin)
        self.assertFailed(self._add(oi_problem), "대회와 규칙 유형이 다른 문제입니다")

    def test_problem_in_a_contest_cannot_be_deleted(self):
        """지우면 제출이 함께 사라지고 순위표에 없는 문제 칸이 남는다."""
        self.assertSuccess(self._add())
        resp = self.client.delete(self.reverse("problem_admin_api") + f"?id={self.problem.id}")
        self.assertFailed(resp)
        self.assertIn("대회에서 먼저 빼주세요", resp.data["data"])


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
        ContestProblem.objects.create(contest_id=self.contest["id"], problem=self.problem, order=1)
        self.url = self.reverse("contest_problem_api")

    def test_admin_get_contest_problem_list(self):
        contest_id = self.contest["id"]
        resp = self.client.get(self.url + "?contest_id=" + str(contest_id))
        self.assertSuccess(resp)
        self.assertEqual(len(resp.data["data"]), 1)

    def test_admin_get_one_contest_problem(self):
        contest_id = self.contest["id"]
        # 대회 문제는 대회 안 표시(A, B, C)로 연다
        resp = self.client.get("{}?contest_id={}&problem_id={}".format(self.url, contest_id, "A"))
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["display_id"], "A")

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


class ContestProblemStatusIsolationTest(APITestCase):
    """대회 안 "푼 문제" 표시는 그 대회 안 제출만 본다.

    문제를 복사하지 않으므로 한 문제가 여러 대회와 공개 목록에 동시에 있다.
    범위를 나누지 않으면 대회 밖에서 미리 푼 것이 대회 안에서 풀린 것으로 보인다.
    """
    def setUp(self):
        self.admin = self.create_admin("teacher", "test123", login=False)
        ProblemTag.objects.create(name="test")
        data = copy.deepcopy(DEFAULT_PROBLEM_DATA)
        data.pop("tags")
        data["created_by"] = self.admin
        self.problem = Problem.objects.create(**data)
        self.student = self.create_user("student", "test123")
        self.contest = self._contest("이번 대회")
        ContestProblem.objects.create(contest=self.contest, problem=self.problem, order=1)

    def _contest(self, title):
        return Contest.objects.create(
            title=title, description="d", rule_type="ACM", real_time_rank=True,
            start_time=now() - timedelta(hours=1), end_time=now() + timedelta(hours=1),
            created_by=self.admin, visible=True)

    def _solve(self, contest=None):
        submission = Submission.objects.create(
            problem=self.problem, user=self.student, contest=contest, code="x",
            language="C", result=JudgeStatus.ACCEPTED)
        dispatcher = JudgeDispatcher(submission.id, self.problem.id)
        if contest is None:
            dispatcher.update_problem_status()
        else:
            dispatcher.update_contest_problem_status()

    def _contest_status(self):
        resp = self.client.get(self.reverse("contest_problem_api")
                               + f"?contest_id={self.contest.id}")
        self.assertSuccess(resp)
        return resp.data["data"][0].get("my_status")

    def test_solving_outside_does_not_mark_it_solved_in_the_contest(self):
        self._solve()
        self.assertIsNone(self._contest_status())

    def test_solving_in_another_contest_does_not_leak(self):
        other = self._contest("다른 대회")
        ContestProblem.objects.create(contest=other, problem=self.problem, order=1)
        self._solve(contest=other)
        self.assertIsNone(self._contest_status())

    def test_solving_in_this_contest_marks_it_solved(self):
        self._solve(contest=self.contest)
        self.assertEqual(self._contest_status(), JudgeStatus.ACCEPTED)

    def test_public_list_still_shows_it_solved(self):
        """대회 밖에서 푼 것은 공개 목록에 그대로 남는다."""
        self._solve()
        resp = self.client.get(self.reverse("problem_api") + "?limit=10")
        self.assertSuccess(resp)
        self.assertEqual(resp.data["data"]["results"][0]["my_status"], JudgeStatus.ACCEPTED)


class ContestProblemLabelTest(APITestCase):
    """대회 안 표시(A, B, C)는 저장하지 않고 순서로 만든다."""
    def test_label_and_order_round_trip(self):
        for order, label in ((1, "A"), (2, "B"), (26, "Z")):
            self.assertEqual(contest_problem_label(order), label)
            self.assertEqual(contest_problem_order(label), order)

    def test_beyond_the_alphabet_falls_back_to_the_number(self):
        self.assertEqual(contest_problem_label(27), "27")
        self.assertEqual(contest_problem_order("27"), 27)

    def test_unreadable_label_is_rejected(self):
        # 주소로 아무 값이나 들어온다. 조회 전에 걸러야 한다.
        for value in ("", None, "AB", "가", "0", "-1"):
            self.assertIsNone(contest_problem_order(value))

    def test_problem_number_is_its_primary_key(self):
        self.assertEqual(Problem(id=1000).display_id, "1000")


class ContestProblemOrderUniqueTest(APITestCase):
    """대회 안 순서가 겹치지 않는 것은 DB 가 지킨다.

    contest 가 NULL 이냐 아니냐로 나뉘는 부분 인덱스다. 그냥 유니크로 걸면 공개
    문제끼리도 걸린다(전부 order 가 0 이다).
    """
    def setUp(self):
        self.admin = self.create_super_admin()

    def _make_contest(self, title):
        return Contest.objects.create(
            title=title, description="d", rule_type="ACM", real_time_rank=True,
            start_time=now(), end_time=now() + timedelta(days=1), created_by=self.admin)

    def _problem(self):
        data = copy.deepcopy(DEFAULT_PROBLEM_DATA)
        data.pop("tags")
        return Problem.objects.create(created_by=self.admin, **data)

    def test_duplicate_order_in_one_contest_is_rejected(self):
        """같은 대회에 순서가 겹치면 라벨도 겹친다(A 가 둘)."""
        contest = self._make_contest("c")
        ContestProblem.objects.create(contest=contest, problem=self._problem(), order=1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ContestProblem.objects.create(contest=contest, problem=self._problem(), order=1)

    def test_same_problem_twice_in_one_contest_is_rejected(self):
        contest = self._make_contest("c")
        problem = self._problem()
        ContestProblem.objects.create(contest=contest, problem=problem, order=1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ContestProblem.objects.create(contest=contest, problem=problem, order=2)

    def test_same_order_allowed_in_different_contests(self):
        """대회 안의 A, B, C 는 대회마다 따로 쓴다. 제약이 그것까지 막으면 안 된다."""
        problem = self._problem()
        for i in range(2):
            ContestProblem.objects.create(contest=self._make_contest(f"c{i}"),
                                          problem=problem, order=1)
        self.assertEqual(ContestProblem.objects.filter(order=1).count(), 2)

    def test_one_problem_can_be_in_several_contests(self):
        """같은 문제를 여러 학급 대회에 쓴다. 예전에는 대회마다 복사본이 생겼다."""
        problem = self._problem()
        for i in range(3):
            ContestProblem.objects.create(contest=self._make_contest(f"c{i}"),
                                          problem=problem, order=1)
        self.assertEqual(Problem.objects.count(), 1)
        self.assertEqual(problem.contest_entries.count(), 3)
