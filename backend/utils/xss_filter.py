"""리치 텍스트에서 위험한 HTML 을 걷어낸다.

문제 설명·공지 같은 리치 텍스트는 HTML 로 저장하고 화면에서 v-html 로 그대로
렌더한다. v-html 은 Vue 의 이스케이프를 건너뛰므로 저장 전에 여기서 거르는 것이
사실상 유일한 방어선이다. RichTextField(utils/models.py) 가 저장 시점에 부른다.

nh3(러스트 ammonia 바인딩)를 쓴다. 브라우저와 같은 html5ever 파서로 파싱한 뒤
다시 직렬화하므로, "필터가 본 문서"와 "브라우저가 본 문서"가 어긋나면서 생기는
우회(mXSS)를 피한다. 예전에는 2015년에 멈춘 외부 코드를 그대로 들고 있었다.
"""
import re

import nh3

# 허용 태그는 nh3 기본값을 그대로 쓴다. 편집기(md-editor-v3)가 마크다운을 렌더해
# 내보내는 태그와 기존 데이터의 태그가 모두 들어 있다.
ALLOWED_TAGS = set(nh3.ALLOWED_TAGS)

ALLOWED_ATTRIBUTES = {tag: set(attrs) for tag, attrs in nh3.ALLOWED_ATTRIBUTES.items()}
# 코드 블록 문법 강조에 쓰는 class 다. markdown-it 이 lang-python 처럼 붙여준다.
ALLOWED_ATTRIBUTES["pre"] = {"class"}
ALLOWED_ATTRIBUTES["code"] = {"class"}
# 본문 링크는 새 탭으로 연다. rel="noopener noreferrer" 는 nh3 가 알아서 붙인다.
ALLOWED_ATTRIBUTES["a"] = ALLOWED_ATTRIBUTES.get("a", set()) | {"target"}

# style 은 허용하지 않는다. 예전 필터는 expression 만 걸러서
# position:fixed 로 화면 전체를 덮는 가짜 UI 를 만들 수 있었다. 실제 데이터의
# style 은 color·margin-left·text-align 같은 장식뿐이라 잃는 것이 없다.

# class 는 문법 강조용으로만 열어둔 것이라 값도 거기에 맞는 것만 통과시킨다.
# 그러지 않으면 앱이 쓰는 아무 클래스나 붙여 화면을 흐트러뜨릴 수 있다.
_LANG_CLASS = re.compile(r"^(lang|language)-[\w+#.-]+$")


def _attribute_filter(tag, attr, value):
    """속성별로 한 번 더 본다. None 을 주면 그 속성을 뺀다."""
    if attr == "class":
        return value if _LANG_CLASS.match(value) else None
    return value


def clean_html(value):
    """저장해도 되는 HTML 만 남겨서 돌려준다."""
    return nh3.clean(value or "",
                     tags=ALLOWED_TAGS,
                     attributes=ALLOWED_ATTRIBUTES,
                     attribute_filter=_attribute_filter)
