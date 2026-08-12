"""학생 로그인 실패 잠금.

학생 비밀번호는 숫자 4자리(1만 가지)이고, 로그인 화면이 학교·학년·반·교사를
검색으로 안내하기 때문에 대상 특정이 쉽다. 실패 횟수 제한이 없으면 사실상 무방비다.

계정(학급+번호) 단위로 센다. IP 단위로 세면 한 교실 30명이 같은 공인 IP 를 쓰기 때문에
수업 중에 반 전체가 함께 막힌다.

주의: utils.cache 의 cache 는 Django 캐시 API 와 raw redis 를 함께 노출한다.
혼동을 피하려고 여기서는 Django 캐시 API(set/get/delete + django-redis 의 ttl)만 쓴다.
"""
from utils.cache import cache

MAX_FAILURES = 5
# 잠금 시간은 실패가 누적될수록 늘린다 (5회=1분, 6회=2분, 7회=4분 ... 최대 30분)
BASE_LOCK_SECONDS = 60
MAX_LOCK_SECONDS = 30 * 60
# 실패 기록 자체의 보존 기간
FAILURE_TTL = 60 * 60


def _fail_key(class_id, number):
    return f"student_login_fail:{class_id}:{number}"


def _lock_key(class_id, number):
    return f"student_login_lock:{class_id}:{number}"


def lock_remaining(class_id, number):
    """잠겨 있으면 남은 초, 아니면 0."""
    ttl = cache.ttl(_lock_key(class_id, number))
    return ttl if ttl and ttl > 0 else 0


def record_failure(class_id, number):
    """실패를 기록하고, 잠겼다면 잠금 시간(초)을 돌려준다.

    엄밀히 원자적이지는 않지만, 경합이 나도 시도 몇 번이 더 허용될 뿐이라
    이 용도에서는 충분하다.
    """
    key = _fail_key(class_id, number)
    failures = (cache.get(key) or 0) + 1
    cache.set(key, failures, FAILURE_TTL)

    if failures < MAX_FAILURES:
        return 0
    over = failures - MAX_FAILURES
    seconds = min(BASE_LOCK_SECONDS * (2 ** over), MAX_LOCK_SECONDS)
    cache.set(_lock_key(class_id, number), 1, seconds)
    return seconds


def clear_login_failures(class_id, number):
    """로그인 성공 또는 교사가 비밀번호를 초기화했을 때 호출한다."""
    cache.delete(_fail_key(class_id, number))
    cache.delete(_lock_key(class_id, number))
