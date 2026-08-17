from django.core.management.base import BaseCommand

from problem.models import ProblemTag


# 기본 문제 태그.
#
# 이름은 교사가 쓰는 말로 짓고, 학생 화면(블록 카테고리)이나 영어 용어는 별칭에 넣는다.
# 별칭은 검색에만 쓰이므로 화면을 어지럽히지 않는다.
#
# 앞쪽은 초등 수업에서 바로 고르는 개념 축이고, 뒤쪽은 상위 프로젝트에서 온 알고리즘
# 분류다. 문제 목록의 태그 사이드바는 문제가 하나라도 붙은 태그만 보여주므로
# (ProblemTagAPI), 쓰이지 않는 태그를 남겨둬도 화면에는 나오지 않는다.
#
# 참조 데이터 시드는 마이그레이션이 아니라 관리 명령으로 둔다.
# (마이그레이션을 다시 생성해도 영향받지 않고, 여러 번 실행해도 안전하다)
DEFAULT_TAGS = [
    # --- 개념: 블록 코딩 카테고리와 같은 축 ---
    ("입출력", ["io", "입력", "출력"]),
    ("조건", ["논리", "선택", "if", "condition"]),
    ("반복", ["loop", "for", "while", "반복문"]),
    ("리스트", ["list", "배열", "array"]),
    ("문자열", ["텍스트", "string", "text"]),
    ("수학", ["math", "연산", "사칙연산"]),
    ("변수", ["variable"]),
    ("함수", ["function", "def"]),
    ("정렬", ["sorting", "sort"]),
    ("구현", ["implementation", "시뮬레이션"]),

    # --- 알고리즘: 해당하는 문제가 생기면 그때 쓰인다 ---
    ("자료 구조", ["data_structures"]),
    ("동적계획법", ["dp", "dynamic_programming"]),
    ("그래프 이론", ["graphs"]),
    ("그래프 탐색", ["graph_traversal"]),
    ("그리디 알고리즘", ["greedy"]),
    ("브루트포스 알고리즘", ["bruteforcing", "bruteforce"]),
]


class Command(BaseCommand):
    help = "기본 문제 태그를 만들고 별칭을 채운다. 여러 번 실행해도 안전하다."

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for name, aliases in DEFAULT_TAGS:
            tag, is_new = ProblemTag.objects.get_or_create(name=name)
            if is_new:
                created += 1
            # 이미 있는 별칭은 그대로 두고 빠진 것만 더한다.
            # (관리자가 손으로 넣은 별칭을 덮어쓰지 않기 위해서다)
            missing = [a for a in aliases if a not in (tag.aliases or [])]
            if missing:
                tag.aliases = (tag.aliases or []) + missing
                tag.save(update_fields=["aliases"])
                updated += 1
        self.stdout.write(self.style.SUCCESS(
            f"기본 태그 {created}개 생성, 별칭 {updated}개 보강 (총 {len(DEFAULT_TAGS)}개 확인)"))
