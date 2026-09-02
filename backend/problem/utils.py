import re
from functools import lru_cache

from django.db.models import Q

from utils.shortcuts import int_or_none

# 문제 번호는 pk 라 정수 컬럼 범위를 넘는 값으로 조회하면 DB 가 거절한다.
# 주소와 검색창에는 아무 값이나 들어오므로 여기서 걸러낸다.
_MAX_PROBLEM_ID = 2147483647


def problem_id_or_none(value):
    """주소나 검색창에서 온 문제 번호. 번호로 볼 수 없으면 None."""
    number = int_or_none(value)
    if number is None or not 0 < number <= _MAX_PROBLEM_ID:
        return None
    return number


TEMPLATE_BASE = """//PREPEND BEGIN
{}
//PREPEND END

//TEMPLATE BEGIN
{}
//TEMPLATE END

//APPEND BEGIN
{}
//APPEND END"""


@lru_cache(maxsize=100)
def parse_problem_template(template_str):
    prepend = re.findall(r"//PREPEND BEGIN\n([\s\S]+?)//PREPEND END", template_str)
    template = re.findall(r"//TEMPLATE BEGIN\n([\s\S]+?)//TEMPLATE END", template_str)
    append = re.findall(r"//APPEND BEGIN\n([\s\S]+?)//APPEND END", template_str)
    return {"prepend": prepend[0] if prepend else "",
            "template": template[0] if template else "",
            "append": append[0] if append else ""}


@lru_cache(maxsize=100)
def build_problem_template(prepend, template, append):
    return TEMPLATE_BASE.format(prepend, template, append)


def normalize_tag_aliases(aliases):
    ret = []
    seen = set()
    for alias in aliases or []:
        alias = alias.strip()
        if alias and alias not in seen:
            ret.append(alias)
            seen.add(alias)
    return ret


def normalize_tag_keyword(value):
    return "".join((value or "").lower().split()).replace("_", "").replace("-", "")


def filter_problem_tags_by_keyword(tags, keyword):
    keyword = (keyword or "").strip().lower()
    if not keyword:
        return tags
    normalized_keyword = normalize_tag_keyword(keyword)

    return [
        tag for tag in tags
        if keyword in tag.name.lower() or
        (normalized_keyword and normalized_keyword in normalize_tag_keyword(tag.name)) or
        any(
            keyword in alias.lower() or
            (normalized_keyword and normalized_keyword in normalize_tag_keyword(alias))
            for alias in (tag.aliases or [])
        )
    ]


def filter_problems_by_keyword(problems, keyword):
    """제목으로 찾고, 숫자를 넣으면 그 번호의 문제도 함께 찾는다.

    번호가 pk 라 부분 일치("100" 으로 1000 찾기)는 뜻이 없다. 정확히 그 번호만 본다.
    """
    keyword = (keyword or "").strip()
    if not keyword:
        return problems
    condition = Q(title__icontains=keyword)
    number = problem_id_or_none(keyword)
    if number is not None:
        condition |= Q(id=number)
    return problems.filter(condition)
