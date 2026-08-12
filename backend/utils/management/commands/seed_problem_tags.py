from django.core.management.base import BaseCommand

from problem.models import ProblemTag


# 기본 제공 문제 태그. 별칭은 검색 편의를 위한 것이다.
# 참조 데이터 시드는 마이그레이션이 아니라 관리 명령으로 둔다.
# (마이그레이션을 다시 생성해도 영향받지 않고, 여러 번 실행해도 안전하다)
DEFAULT_TAGS = [
    ("수학", ["math"]),
    ("구현", ["implementation"]),
    ("동적계획법", ["dp", "dynamic_programming"]),
    ("자료 구조", ["data_structures"]),
    ("그래프 이론", ["graphs"]),
    ("그리디 알고리즘", ["greedy"]),
    ("문자열", ["string"]),
    ("브루트포스 알고리즘", ["bruteforcing", "bruteforce"]),
    ("그래프 탐색", ["graph_traversal"]),
    ("정렬", ["sorting", "sort"]),
]


class Command(BaseCommand):
    help = "기본 문제 태그를 생성한다. 여러 번 실행해도 안전하다."

    def handle(self, *args, **options):
        created = 0
        for name, aliases in DEFAULT_TAGS:
            tag, is_new = ProblemTag.objects.get_or_create(name=name)
            if is_new:
                created += 1
            if not tag.aliases:
                tag.aliases = aliases
                tag.save(update_fields=["aliases"])
        self.stdout.write(self.style.SUCCESS(
            f"기본 태그 {created}개 생성 (총 {len(DEFAULT_TAGS)}개 확인)"))
