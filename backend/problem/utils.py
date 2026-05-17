import re
from functools import lru_cache


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
