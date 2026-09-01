# 대회 문제의 표시 라벨(A, B, C)을 _id 에서 order 로 옮긴다.
#
# _id 가 공개 문제의 표시 번호("1000")와 대회 문제의 라벨("A") 두 가지를 함께
# 담고 있어서, 정렬 규칙 하나로 숫자와 알파벳을 모두 처리해야 했다. 대회 라벨을
# order 로 떼어내면 _id 는 공개 문제 번호만 뜻하게 된다.
from collections import defaultdict

from django.db import migrations, models
import django.db.models.functions.text

# 이 시점의 모델 기본 정렬은 (Length("_id"), "_id") 다. 정렬을 지우지 않으면 정렬
# 컬럼이 SELECT 에 함께 실려 distinct 가 대회마다 여러 줄을 돌려주고, _id 를 비우는
# 도중에 같은 대회를 다시 집어 번호를 덮어쓴다. 그래서 order_by() 로 지우고
# list() 로 한 번에 읽어둔 다음 고친다.


def _by_contest(Problem):
    rows = list(Problem.objects.filter(contest__isnull=False)
                .order_by().values_list("id", "contest_id", "_id", "order"))
    grouped = defaultdict(list)
    for pk, contest_id, label, order in rows:
        grouped[contest_id].append((pk, label, order))
    return grouped


def split_contest_label(apps, schema_editor):
    """대회 문제의 _id(A, B, C)를 order(1, 2, 3)로 옮기고 _id 를 비운다."""
    Problem = apps.get_model("problem", "Problem")
    for problems in _by_contest(Problem).values():
        # 옛 라벨 순서를 그대로 지킨다. 라벨이 아닌 값이 섞여 있어도 뒤로 밀릴 뿐이다.
        problems.sort(key=lambda row: (len(row[1] or ""), row[1] or ""))
        for order, (pk, _label, _order) in enumerate(problems, start=1):
            Problem.objects.filter(id=pk).update(order=order, _id=None)


def restore_contest_label(apps, schema_editor):
    Problem = apps.get_model("problem", "Problem")
    labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for problems in _by_contest(Problem).values():
        for pk, _label, order in problems:
            restored = labels[order - 1] if 1 <= order <= len(labels) else str(order)
            Problem.objects.filter(id=pk).update(_id=restored)


class Migration(migrations.Migration):

    dependencies = [
        ("problem", "0006_unique_public_display_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="problem",
            name="order",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="problem",
            name="_id",
            field=models.TextField(db_index=True, null=True),
        ),
        # ("_id", "contest") 유니크는 대회 문제만 막고 있었다. 대회 문제의 _id 가
        # 비면 아무것도 막지 않으므로 걷어내고, 아래에서 order 로 다시 건다.
        migrations.AlterUniqueTogether(
            name="problem",
            unique_together=set(),
        ),
        migrations.RunPython(split_contest_label, restore_contest_label),
        migrations.AddConstraint(
            model_name="problem",
            constraint=models.UniqueConstraint(
                condition=models.Q(("contest__isnull", False)),
                fields=("contest", "order"),
                name="uniq_contest_problem_order",
            ),
        ),
        migrations.AlterModelOptions(
            name="problem",
            options={"ordering": ("order", django.db.models.functions.text.Length("_id"), "_id")},
        ),
    ]
