from django.db import migrations, models
from django.db.models import Q


def _resolve_duplicates(apps, schema_editor):
    """이미 겹쳐 있는 표시 번호를 풀어준다. 없으면 아무 것도 하지 않는다.

    제약을 거는 순간 중복이 있으면 마이그레이션 자체가 실패한다. 중복은 교사 둘이
    거의 동시에 문제를 만들 때 생겼고(next_display_id 가 읽기-쓰기 사이에 막혀
    있지 않다), DB 도 막아주지 않아 조용히 쌓였다.

    나중에 만들어진 쪽(id 가 큰 쪽)에 새 번호를 준다. 먼저 만들어진 문제의 번호가
    바뀌면 이미 그 번호로 알려진 문제가 달라지기 때문이다.
    """
    Problem = apps.get_model("problem", "Problem")

    public = Problem.objects.filter(contest__isnull=True)
    seen = set()
    duplicates = []
    for pk, display_id in public.order_by("id").values_list("id", "_id"):
        if display_id in seen:
            duplicates.append(pk)
        else:
            seen.add(display_id)
    if not duplicates:
        return

    numbers = [int(v) for v in seen if str(v).isdigit()]
    nxt = max(numbers) + 1 if numbers else 1000
    for pk in duplicates:
        while str(nxt) in seen:
            nxt += 1
        seen.add(str(nxt))
        Problem.objects.filter(id=pk).update(_id=str(nxt))
        nxt += 1


class Migration(migrations.Migration):
    """공개 문제의 표시 번호를 DB 에서 유일하게 만든다.

    unique_together(("_id", "contest")) 는 대회 문제만 막아준다. 공개 문제는
    contest 가 NULL 인데, 유니크 인덱스에서 NULL 은 서로 다른 값이라 같은 번호가
    몇 개든 들어갔다.
    """

    dependencies = [
        ("problem", "0005_problem_visibility"),
    ]

    operations = [
        migrations.RunPython(_resolve_duplicates, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="problem",
            constraint=models.UniqueConstraint(
                condition=Q(contest__isnull=True),
                fields=("_id",),
                name="uniq_public_display_id"),
        ),
    ]
