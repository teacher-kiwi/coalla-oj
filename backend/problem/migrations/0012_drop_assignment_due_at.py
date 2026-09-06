from django.db import migrations


class Migration(migrations.Migration):
    """문제집 배포에서 마감일을 없앤다.

    지나도 아무것도 막지 않는 표시용이라 역할이 없었다. 되돌리면 컬럼은
    비어 있는 채로 살아난다(적어둔 마감일은 돌아오지 않는다).
    """

    dependencies = [
        ("problem", "0011_drop_assignment_is_open"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="problemsetassignment",
            name="due_at",
        ),
    ]
