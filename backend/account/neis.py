"""나이스(NEIS) 학교 기본정보 적재.

학교명을 자유 입력으로 두면 표기가 흔들려("서울초" vs "서울초등학교")
학생이 자기 학급을 찾지 못한다. 그래서 목록을 미리 심어두고 고르게 한다.

전국 학교가 1만 개가 넘고 API 가 한 번에 최대 1,000건씩 주므로
동기 요청으로는 타임아웃이 난다. dramatiq 백그라운드 작업으로 돌린다.

API 문서: https://open.neis.go.kr  (학교기본정보)
"""
import logging

import requests

from options.options import SysOptions
from .models import School

logger = logging.getLogger(__name__)

NEIS_URL = "https://open.neis.go.kr/hub/schoolInfo"
PAGE_SIZE = 1000
# 무한 루프 방지. 1000건씩이므로 30페이지면 3만 개까지 커버한다.
MAX_PAGES = 30
REQUEST_TIMEOUT = 30

# 학생이 쓰는 학교 종류만 담는다(유치원·각종학교 등은 제외).
WANTED_KINDS = ("초등학교", "중학교", "고등학교", "특수학교")


class NeisError(Exception):
    pass


def _fetch_page(api_key, page):
    """한 페이지를 가져와 (rows, total) 를 돌려준다."""
    try:
        resp = requests.get(NEIS_URL, timeout=REQUEST_TIMEOUT, params={
            "KEY": api_key,
            "Type": "json",
            "pIndex": page,
            "pSize": PAGE_SIZE,
        })
        resp.raise_for_status()
        body = resp.json()
    except requests.RequestException as e:
        raise NeisError(f"나이스 API 호출에 실패했습니다: {e}")
    except ValueError:
        raise NeisError("나이스 API 응답을 해석할 수 없습니다")

    # 오류일 때는 {"RESULT": {"CODE": ..., "MESSAGE": ...}} 형태로 온다
    if "RESULT" in body:
        code = body["RESULT"].get("CODE", "")
        message = body["RESULT"].get("MESSAGE", "")
        if code == "INFO-200":       # 해당 데이터 없음 = 마지막 페이지 다음
            return [], 0
        raise NeisError(f"나이스 API 오류({code}): {message}")

    try:
        blocks = body["schoolInfo"]
        head = blocks[0]["head"]
        total = head[0]["list_total_count"]
        result_code = head[1]["RESULT"]["CODE"]
        rows = blocks[1]["row"]
    except (KeyError, IndexError, TypeError):
        raise NeisError("나이스 API 응답 형식이 예상과 다릅니다")

    if result_code != "INFO-000":
        raise NeisError(f"나이스 API 오류({result_code})")
    return rows, total


def _to_school(row):
    return School(
        code=row.get("SD_SCHUL_CODE", "").strip(),
        name=(row.get("SCHUL_NM") or "").strip(),
        kind=(row.get("SCHUL_KND_SC_NM") or "").strip(),
        office=(row.get("ATPT_OFCDC_SC_NM") or "").strip(),
        address=(row.get("ORG_RDNMA") or "").strip(),
    )


def sync_schools(api_key, progress=None):
    """전체 학교를 내려받아 저장한다. 저장한 건수를 돌려준다.

    progress: 진행 상황을 알릴 콜백 (처리건수, 전체건수)
    """
    if not api_key:
        raise NeisError("나이스 API 키가 설정되지 않았습니다")

    seen = 0
    saved = 0
    for page in range(1, MAX_PAGES + 1):
        rows, total = _fetch_page(api_key, page)
        if not rows:
            break

        # 학교코드를 먼저 정규화한 뒤 거른다.
        # 개교 예정인 "(가칭)" 학교는 SD_SCHUL_CODE 가 공백이라 truthy 검사만으로는 통과해버린다.
        # 또 한 페이지에 같은 코드가 두 번 오면 ON CONFLICT 가 같은 행을 두 번 갱신하려다
        # 실패하므로, 코드를 키로 하는 dict 로 배치 안 중복을 없앤다.
        by_code = {}
        for row in rows:
            code = (row.get("SD_SCHUL_CODE") or "").strip()
            kind = (row.get("SCHUL_KND_SC_NM") or "").strip()
            if not code or kind not in WANTED_KINDS:
                continue
            by_code[code] = _to_school(row)

        schools = list(by_code.values())
        if schools:
            # 학교코드가 unique 이므로 있으면 갱신, 없으면 추가한다.
            School.objects.bulk_create(
                schools,
                update_conflicts=True,
                unique_fields=["code"],
                update_fields=["name", "kind", "office", "address"],
            )
            saved += len(schools)

        seen += len(rows)
        if progress:
            progress(seen, total)
        if seen >= total:
            break
    else:
        logger.warning("나이스 학교 적재가 최대 페이지(%s)에 도달했습니다", MAX_PAGES)

    return saved


def set_status(**kwargs):
    """적재 진행 상황을 SysOptions 에 남긴다(관리자 화면에서 조회).

    updated_at 을 항상 남긴다. 워커가 도중에 죽으면 state 가 running 인 채로
    남아 다시 시작할 수 없게 되는데, 이 값으로 "멈춘 작업"을 판별한다.
    """
    from django.utils.timezone import now
    status = dict(SysOptions.school_sync_status or {})
    status.update(kwargs)
    status["updated_at"] = now().isoformat()
    SysOptions.school_sync_status = status
    return status


# 이 시간 넘게 갱신이 없으면 죽은 작업으로 보고 재시작을 허용한다.
STALE_AFTER_SECONDS = 10 * 60


def is_running():
    """정말로 진행 중인지. 오래 갱신되지 않았으면 죽은 것으로 본다."""
    from django.utils.dateparse import parse_datetime
    from django.utils.timezone import now
    status = SysOptions.school_sync_status or {}
    if status.get("state") != "running":
        return False
    updated = parse_datetime(status.get("updated_at") or "")
    if not updated:
        return False
    return (now() - updated).total_seconds() < STALE_AFTER_SECONDS
