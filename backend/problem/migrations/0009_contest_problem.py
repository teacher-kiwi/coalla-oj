# 대회 문제를 복사본에서 관계로 바꾼다.
#
# 예전에는 문제를 복사해서 대회에 넣었다(Problem.contest FK). 같은 문제를 세 반
# 대회에 쓰면 세 벌이 생겼고, 대회가 끝나고 공개로 돌리면 또 한 벌이 더 생겨
# 대회 때의 제출 기록이 따라오지 않았다.
#
# 기존 복사본은 원본으로 되돌려 합칠 수 없다(어느 문제를 복사한 것인지 남겨둔
# 정보가 없다). 그래서 복사본을 그대로 비공개 문제로 두고 관계만 새로 잇는다.
from django.db import migrations, models
import django.db.models.deletion

import utils.models


def link_contest_problems(apps, schema_editor):
    Problem = apps.get_model("problem", "Problem")
    ContestProblem = apps.get_model("problem", "ContestProblem")
    rows = list(Problem.objects.filter(contest__isnull=False)
                .order_by().values_list("id", "contest_id", "order",
                                        "submission_number", "accepted_number",
                                        "statistic_info"))
    ContestProblem.objects.bulk_create([
        ContestProblem(problem_id=pk, contest_id=contest_id, order=order,
                       submission_number=submissions, accepted_number=accepted,
                       statistic_info=info)
        for pk, contest_id, order, submissions, accepted, info in rows
    ])


def unlink_contest_problems(apps, schema_editor):
    Problem = apps.get_model("problem", "Problem")
    ContestProblem = apps.get_model("problem", "ContestProblem")
    for entry in ContestProblem.objects.all():
        Problem.objects.filter(id=entry.problem_id).update(
            contest_id=entry.contest_id, order=entry.order,
            submission_number=entry.submission_number,
            accepted_number=entry.accepted_number,
            statistic_info=entry.statistic_info)
    ContestProblem.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("contest", "0002_class_contest"),
        ("problem", "0008_drop_display_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="ContestProblem",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True,
                                        serialize=False, verbose_name="ID")),
                ("order", models.PositiveIntegerField()),
                ("submission_number", models.BigIntegerField(default=0)),
                ("accepted_number", models.BigIntegerField(default=0)),
                ("statistic_info", utils.models.JSONField(default=dict)),
                ("contest", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                              related_name="problems", to="contest.contest")),
                ("problem", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                              related_name="contest_entries", to="problem.problem")),
            ],
            options={
                "db_table": "contest_problem",
                "ordering": ("order",),
                "unique_together": {("contest", "problem"), ("contest", "order")},
            },
        ),
        migrations.RunPython(link_contest_problems, unlink_contest_problems),
        migrations.RemoveConstraint(
            model_name="problem",
            name="uniq_contest_problem_order",
        ),
        migrations.RemoveField(model_name="problem", name="contest"),
        migrations.RemoveField(model_name="problem", name="order"),
        migrations.RemoveField(model_name="problem", name="is_public"),
        migrations.AlterModelOptions(
            name="problem",
            options={"ordering": ("id",)},
        ),
    ]
