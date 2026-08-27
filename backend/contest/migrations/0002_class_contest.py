from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """교사가 자기 학급을 대상으로 여는 대회."""

    dependencies = [
        ("account", "0006_student_username_and_nickname"),
        ("contest", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="contest",
            name="is_class_contest",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="ClassContestAssignment",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True,
                                        serialize=False, verbose_name="ID")),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                ("contest", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                              related_name="assignments", to="contest.contest")),
                ("school_class", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                   related_name="contest_assignments",
                                                   to="account.schoolclass")),
            ],
            options={
                "db_table": "class_contest_assignment",
                "ordering": ("-assigned_at",),
                "unique_together": {("contest", "school_class")},
            },
        ),
    ]
