from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """문제 즐겨찾기."""

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("problem", "0012_drop_assignment_due_at"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProblemFavorite",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True,
                                        serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("problem", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                              related_name="favorites", to="problem.problem")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                           related_name="problem_favorites",
                                           to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "problem_favorite",
                "ordering": ("-created_at",),
                "unique_together": {("user", "problem")},
            },
        ),
    ]
