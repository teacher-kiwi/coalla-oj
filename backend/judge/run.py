"""학생이 문제 화면에서 자기 입력으로 코드를 한 번 돌려 보는 기능.

제출하기 전에 print 로 중간 값을 찍어 보며 고치는 것이 목적이다. 그래서
정답과 비교하지 않고, 프로그램이 찍은 출력(오류 메시지 포함)을 그대로 돌려준다.
채점 서버는 stderr 를 출력 파일에 함께 쓰므로 파이썬의 Traceback 도 보인다.

제출(Submission)을 만들지 않는다. 통계·순위·"푼 문제" 어디에도 남지 않는다.

제출을 밀어내면 안 된다. 수업이나 대회에서 여럿이 동시에 누르면 그만큼 채점이
늦어지므로, 빈 채점 서버가 없으면 기다리지 않고 바로 "바쁘다" 고 돌려준다.
(정답 코드 검증은 몇 분이라도 기다리지만, 실행은 금방 다시 누를 수 있다)
"""
import logging
import uuid
from urllib.parse import urljoin

from options.options import SysOptions
from submission.models import JudgeStatus
from utils.cache import cache
from utils.constants import CacheKey

from .dispatcher import ChooseJudgeServer, DispatcherBase

logger = logging.getLogger(__name__)

# 화면으로 돌려주는 출력의 상한. 채점기는 16MB 까지 허용해서, 반복문에서 print 를
# 멈추지 않으면 그만큼이 브라우저로 간다. 디버깅에는 앞부분이면 충분하다.
MAX_OUTPUT_BYTES = 64 * 1024
# 결과를 캐시에 두는 시간. 화면이 가져가면 끝이라 짧아도 된다.
PENDING_SECONDS = 10 * 60

# 채점기의 결과 코드를 화면이 알아듣는 말로 바꾼다.
# 정답을 주지 않으므로 정답(0)과 오답(-1)은 모두 "정상으로 끝났다" 이다.
RESULTS = {
    JudgeStatus.ACCEPTED: "ok",
    JudgeStatus.WRONG_ANSWER: "ok",
    JudgeStatus.CPU_TIME_LIMIT_EXCEEDED: "time_limit",
    JudgeStatus.REAL_TIME_LIMIT_EXCEEDED: "time_limit",
    JudgeStatus.MEMORY_LIMIT_EXCEEDED: "memory_limit",
    JudgeStatus.RUNTIME_ERROR: "runtime_error",
}


def _key(token):
    return CacheKey.run + token


def start_run(user_id):
    """실행을 걸고 표를 돌려준다. 표는 건 사람만 읽을 수 있다."""
    token = uuid.uuid4().hex
    cache.set(_key(token), {"status": "running", "user_id": user_id}, PENDING_SECONDS)
    return token


def read_run(token, user_id):
    record = cache.get(_key(token)) if token else None
    # 남의 표로 남의 코드 출력을 읽을 수 없게 한다
    if not record or record.get("user_id") != user_id:
        return None
    return record


class CodeRunner(DispatcherBase):
    """코드를 입력 하나로 한 번 돌리고 출력을 받아 온다."""

    def __init__(self, spec):
        super().__init__()
        self.spec = spec

    def _payload(self):
        config = next((item for item in SysOptions.languages
                       if item["name"] == self.spec["language"]), None)
        if config is None:
            return None
        return {
            "language_config": config["config"],
            "src": self.spec["code"],
            "max_cpu_time": self.spec["time_limit"],
            "max_memory": 1024 * 1024 * self.spec["memory_limit"],
            # 정답을 모르므로 빈 출력을 준다. 판정은 버리고 출력만 쓴다.
            "test_case": [{"input": self.spec["input"], "output": ""}],
            "output": True,
            "io_mode": self.spec.get("io_mode") or {"io_mode": "Standard IO"},
        }

    def run(self):
        """:return: 화면에 줄 결과 사전"""
        data = self._payload()
        if data is None:
            language = self.spec["language"]
            return {"result": "system_error", "message": f"언어 {language} 의 설정이 없습니다"}

        with ChooseJudgeServer() as server:
            if not server:
                return {"result": "busy",
                        "message": "지금 채점 서버가 바쁩니다. 잠시 뒤 다시 실행해주세요"}
            resp = self._request(urljoin(server.service_url, "/judge"), data=data)

        if not resp:
            return {"result": "system_error", "message": "채점 서버에 연결하지 못했습니다"}
        if resp["err"]:
            if resp["err"] == "CompileError":
                return {"result": "compile_error", "message": str(resp["data"])}
            return {"result": "system_error", "message": str(resp["data"])}

        case = resp["data"][0]
        output = case.get("output") or ""
        encoded = output.encode("utf-8")
        truncated = len(encoded) > MAX_OUTPUT_BYTES
        if truncated:
            output = encoded[:MAX_OUTPUT_BYTES].decode("utf-8", errors="ignore")
        return {
            "result": RESULTS.get(case["result"], "system_error"),
            "output": output,
            "truncated": truncated,
            "time": case.get("cpu_time"),
            "memory": case.get("memory"),
        }


def run_code(token, user_id, spec):
    """돌리고 결과를 캐시에 적는다."""
    try:
        result = CodeRunner(spec).run()
    except Exception as e:
        logger.exception(e)
        result = {"result": "system_error", "message": "실행 중 오류가 났습니다"}
    cache.set(_key(token), {"status": "done", "user_id": user_id, **result}, PENDING_SECONDS)
    return result
