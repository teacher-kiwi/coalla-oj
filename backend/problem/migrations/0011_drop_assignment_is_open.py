from django.db import migrations


def drop_closed_assignments(apps, schema_editor):
    """공개를 꺼 둔 배포는 지운다.

    학생 화면은 지금까지 is_open=True 인 배포만 봤다. 컬럼만 없애면 꺼 둔
    문제집이 갑자기 학생에게 보이므로, 배포를 지워 보이지 않는 상태를 유지한다.
    """
    apps.get_model("problem", "ProblemSetAssignment").objects.filter(is_open=False).delete()


class Migration(migrations.Migration):
    """배포와 공개를 배포 하나로 합친다.

    되돌리면 컬럼이 기본값 True 로 살아난다. 지워진 배포는 돌아오지 않는다.
    """

    dependencies = [
        ("problem", "0010_contest_status_per_contest"),
    ]

    operations = [
        migrations.RunPython(drop_closed_assignments, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="problemsetassignment",
            name="is_open",
        ),
    ]
