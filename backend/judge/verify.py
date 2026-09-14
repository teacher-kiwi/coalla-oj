"""출제자가 넣은 정답 코드로 테스트케이스가 맞는지 확인한다.

테스트케이스를 잘못 만들면 학생이 제대로 풀어도 오답이 나온다. 초등학생은
자기 코드를 의심하지 문제를 의심하지 않아서, 조용히 학생을 좌절시키는 실패다.
정답 코드를 한 번 돌려 보면 그런 케이스를 출제 단계에서 잡을 수 있다.

이것은 참고용 도구다. 넣지 않아도 되고, 통과하지 못해도 저장을 막지 않는다.
정답을 만들어 내지도 않는다 - 이미 넣어 둔 출력과 맞는지 볼 뿐이라, 정답
코드가 틀렸으면 데이터가 오염되는 것이 아니라 경고가 뜬다.

제출(Submission)을 만들지 않는다. 통계·순위·"푼 문제" 어디에도 남지 않는다.

문제를 저장하기 전에도 돌린다. 검증이 가장 필요한 때가 문제를 만드는 중이라
저장을 먼저 시키면 순서가 거꾸로다. 그래서 결과를 문제가 아니라 캐시에 잠시
두고, 저장할 때 옮겨 붙인다.

옮겨 붙일 때는 지문을 대조한다. "검증 → 케이스 수정 → 저장" 순서면 저장되는
내용은 검증한 적이 없는데도 "통과함" 이 붙기 때문이다. 대조는 서버가 한다.
화면이 "이 결과는 이 내용의 것" 이라고 말하게 하면 믿을 것이 못 된다.
"""
import hashlib
import json
import logging
import os
import shutil
import time
import uuid
from urllib.parse import urljoin

from django.conf import settings
from django.utils.timezone import now

from options.options import SysOptions
from problem.models import Problem
from submission.models import JudgeStatus
from utils.cache import cache
from utils.constants import CacheKey

from .dispatcher import ChooseJudgeServer, DispatcherBase

logger = logging.getLogger(__name__)

# 빈 채점 서버가 없을 때 기다리는 간격과 횟수(재채점과 같은 규칙).
# 검증은 저장과 분리돼 있어 몇 분 걸려도 사람을 붙들지 않는다.
BUSY_WAIT_SECONDS = 5
BUSY_RETRIES = 60

# 왜 통과하지 못했는지 사람 말로 알려준다
RESULT_MESSAGES = {
    JudgeStatus.WRONG_ANSWER: "넣어 둔 출력과 다릅니다",
    JudgeStatus.CPU_TIME_LIMIT_EXCEEDED: "시간이 초과했습니다",
    JudgeStatus.REAL_TIME_LIMIT_EXCEEDED: "시간이 초과했습니다",
    JudgeStatus.MEMORY_LIMIT_EXCEEDED: "메모리가 초과했습니다",
    JudgeStatus.RUNTIME_ERROR: "실행 중 오류가 났습니다",
    JudgeStatus.SYSTEM_ERROR: "채점 중 오류가 났습니다",
}


# 판정을 좌우하는 것들. 하나라도 달라지면 지난 결과는 그 내용의 것이 아니다.
# resolved_test_case_id 는 여기 없다. 검증하려고 잠시 만든 묶음의 id 라 매번
# 달라지는데, 판정을 좌우하는 것은 그 안의 내용(cases)이지 id 가 아니다.
FINGERPRINT_FIELDS = ("solver_language", "solver_code", "test_case_id", "cases",
                      "spj_language", "spj_code", "time_limit", "memory_limit")


def fingerprint(spec):
    """무엇을 검증했는지 나타내는 지문."""
    material = json.dumps({key: spec.get(key) for key in FINGERPRINT_FIELDS},
                          sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class SolutionVerifier(DispatcherBase):
    """정답 코드를 테스트케이스로 한 번 돌린다.

    spec 은 문제에서 뽑을 수도 있고 아직 저장하지 않은 화면 내용일 수도 있다.
    케이스는 이미 올려둔 test_case_id 이거나, 직접 입력한 cases 다.
    """

    def __init__(self, spec):
        super().__init__()
        self.spec = spec

    def _payload(self):
        language = self.spec.get("solver_language")
        config = next((item for item in SysOptions.languages if item["name"] == language), None)
        if config is None:
            return None
        spj_config = {}
        if self.spec.get("spj_code"):
            for lang in SysOptions.spj_languages:
                if lang["name"] == self.spec.get("spj_language"):
                    spj_config = lang["spj"]
                    break
        data = {
            "language_config": config["config"],
            "src": self.spec["solver_code"],
            "max_cpu_time": self.spec["time_limit"],
            "max_memory": 1024 * 1024 * self.spec["memory_limit"],
            "output": False,
            "spj_version": self.spec.get("spj_version"),
            "spj_config": spj_config.get("config"),
            "spj_compile_config": spj_config.get("compile"),
            "spj_src": self.spec.get("spj_code"),
            "io_mode": self.spec.get("io_mode") or {"io_mode": "Standard IO"},
        }
        # 채점 서버는 test_case_id 로 디스크의 묶음을 읽는다. 화면이 보낸 케이스는
        # 저장할 때와 똑같이 파일로 만들어 두고(resolved_test_case_id) 그 id 를 준다.
        # 인라인으로 넘기면 {"keep": 번호} 처럼 내용이 없는 항목을 풀 수 없다.
        data["test_case_id"] = self.spec.get("resolved_test_case_id") or self.spec["test_case_id"]
        return data

    def run(self, sleep=time.sleep):
        """:return: (passed, message)"""
        data = self._payload()
        if data is None:
            language = self.spec.get("solver_language")
            return False, f"언어 {language} 의 설정이 없습니다"

        resp = None
        for _ in range(BUSY_RETRIES):
            with ChooseJudgeServer() as server:
                if server:
                    resp = self._request(urljoin(server.service_url, "/judge"), data=data)
                    break
            sleep(BUSY_WAIT_SECONDS)
        else:
            return False, "채점 서버가 계속 바빠 확인하지 못했습니다. 잠시 뒤 다시 눌러주세요"

        if not resp:
            return False, "채점 서버에 연결하지 못했습니다"
        if resp["err"]:
            # 컴파일 실패는 "케이스가 틀렸다" 가 아니라 "확인하지 못했다" 이다
            return False, "정답 코드가 컴파일되지 않습니다\n" + str(resp["data"])

        results = resp["data"]
        failed = [case for case in results if case["result"] != JudgeStatus.ACCEPTED]
        if not failed:
            return True, f"테스트 케이스 {len(results)}개를 모두 통과했습니다"
        first = min(failed, key=lambda case: int(case["test_case"]))
        number = first["test_case"]
        reason = RESULT_MESSAGES.get(first["result"], "통과하지 못했습니다")
        return False, f"{number}번 케이스에서 {reason} (통과하지 못한 케이스 {len(failed)}개)"


def spec_from(data, *, time_limit, memory_limit, io_mode=None):
    """화면이 보낸 내용에서 검증에 필요한 것만 뽑는다.

    교사 화면과 관리자 화면이 서로 다른 폼을 쓰지만, 판정을 좌우하는 값은 같다.
    시간·메모리 제한은 교사 화면이 받지 않아(서버가 기본값을 채운다) 밖에서 준다.
    """
    return {
        "solver_language": data.get("solver_language") or None,
        "solver_code": data.get("solver_code") or None,
        "test_case_id": data.get("test_case_id") or None,
        "cases": data.get("cases") or None,
        "spj_language": data.get("spj_language") if data.get("spj") else None,
        "spj_code": data.get("spj_code") if data.get("spj") else None,
        "spj_version": data.get("spj_version"),
        "time_limit": time_limit,
        "memory_limit": memory_limit,
        "io_mode": io_mode,
    }


def spec_of(problem):
    """이미 저장된 문제에서 뽑는다."""
    return spec_from({
        "solver_language": problem.solver_language, "solver_code": problem.solver_code,
        "test_case_id": problem.test_case_id, "spj": problem.spj,
        "spj_language": problem.spj_language, "spj_code": problem.spj_code,
        "spj_version": problem.spj_version,
    }, time_limit=problem.time_limit, memory_limit=problem.memory_limit,
        io_mode=problem.io_mode)


# 검증 결과를 캐시에 두는 시간. 사람이 결과를 보고 저장하기까지 넉넉하면 된다.
PENDING_SECONDS = 30 * 60


def _key(token):
    return CacheKey.verification + token


def start_verification(spec):
    """검증을 걸고 표를 돌려준다. 실제 실행은 뒤에서 돈다."""
    token = uuid.uuid4().hex
    cache.set(_key(token), {"status": "running", "fingerprint": fingerprint(spec)},
              PENDING_SECONDS)
    return token


def read_verification(token):
    return cache.get(_key(token)) if token else None


def run_verification(token, spec, sleep=time.sleep):
    """검증하고 결과를 캐시에 적는다.

    검증하려고 잠시 만든 케이스 묶음은 끝나면 지운다. 문제에 저장되는 것이
    아니라 이 한 번을 위한 것이라, 두면 디스크에 쌓이기만 한다.
    """
    try:
        passed, message = SolutionVerifier(spec).run(sleep=sleep)
    finally:
        if spec.get("resolved_is_temporary") and spec.get("resolved_test_case_id"):
            shutil.rmtree(os.path.join(settings.TEST_CASE_DIR, spec["resolved_test_case_id"]),
                          ignore_errors=True)
    cache.set(_key(token), {"status": "done", "fingerprint": fingerprint(spec),
                            "passed": passed, "message": message}, PENDING_SECONDS)
    return passed, message


def attach_verification(problem, token, spec):
    """저장한 문제에 검증 결과를 옮겨 붙인다.

    검증한 내용과 저장하는 내용이 다르면 붙이지 않는다. 실패가 아니라 그저
    "이 내용은 아직 검증되지 않았다" 이므로 조용히 넘어간다.
    """
    record = read_verification(token)
    if not record or record.get("status") != "done":
        return False
    if record.get("fingerprint") != fingerprint(spec):
        return False
    Problem.objects.filter(id=problem.id).update(
        solver_passed=record["passed"], solver_message=record["message"],
        solver_verified_at=now())
    return True


def clear_verification(problem_id):
    """테스트케이스가 바뀌면 지난 결과를 지운다.

    그대로 두면 "통과함" 이 남아 거짓말이 된다. 정답 코드는 그대로 두어
    출제자가 검증 버튼만 다시 누르면 되게 한다.
    """
    Problem.objects.filter(id=problem_id).update(
        solver_passed=False, solver_message="", solver_verified_at=None)
