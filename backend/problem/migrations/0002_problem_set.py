# 교육용 전환 4단계: 문제집 / 문제집 항목 / 학급 배포
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0003_drop_username_prefix"),
        ("problem", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProblemSet",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.TextField()),
                ("description", models.TextField(blank=True, default="")),
                ("create_time", models.DateTimeField(auto_now_add=True)),
                ("last_update_time", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                 related_name="problem_sets", to="account.user")),
            ],
            options={"db_table": "problem_set", "ordering": ("-create_time",)},
        ),
        migrations.CreateModel(
            name="ProblemSetItem",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.IntegerField(default=0)),
                ("problem", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                              related_name="problem_set_items", to="problem.problem")),
                ("problem_set", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                  related_name="items", to="problem.problemset")),
            ],
            options={
                "db_table": "problem_set_item",
                "ordering": ("order", "id"),
                "unique_together": {("problem_set", "problem")},
            },
        ),
        migrations.CreateModel(
            name="ProblemSetAssignment",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("is_open", models.BooleanField(default=True)),
                ("problem_set", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                  related_name="assignments", to="problem.problemset")),
                ("school_class", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                   related_name="assignments", to="account.schoolclass")),
            ],
            options={
                "db_table": "problem_set_assignment",
                "ordering": ("-assigned_at",),
                "unique_together": {("problem_set", "school_class")},
            },
        ),
    ]
