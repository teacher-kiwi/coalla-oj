from django.db import migrations, models


def number_existing_classes(apps, schema_editor):
    """이미 있는 학급에 지금 보이는 차례대로 1..N 을 매긴다.

    전부 0 으로 두면 순서를 한 번 바꾼 뒤부터 손대지 않은 학급이 앞으로 끼어든다.
    """
    SchoolClass = apps.get_model("account", "SchoolClass")
    rows = list(SchoolClass.objects.order_by("teacher_id", "-year", "grade", "class_no"))
    order_by_teacher = {}
    for row in rows:
        order = order_by_teacher.get(row.teacher_id, 0) + 1
        order_by_teacher[row.teacher_id] = order
        row.order = order
    SchoolClass.objects.bulk_update(rows, ["order"])


class Migration(migrations.Migration):
    """교사가 자기 학급의 차례를 정할 수 있게 한다."""

    dependencies = [
        ("account", "0006_student_username_and_nickname"),
    ]

    operations = [
        migrations.AddField(
            model_name="schoolclass",
            name="order",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(number_existing_classes, migrations.RunPython.noop),
    ]
