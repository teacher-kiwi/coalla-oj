# 교육용 전환 3단계: 학교 / 학급 / 학급 소속
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="School",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.TextField(unique=True)),
                ("name", models.TextField(db_index=True)),
                ("kind", models.TextField(blank=True, default="")),
                ("office", models.TextField(blank=True, default="")),
                ("address", models.TextField(blank=True, default="")),
            ],
            options={"db_table": "school", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="SchoolClass",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.IntegerField()),
                ("grade", models.IntegerField()),
                ("class_no", models.IntegerField()),
                ("username_prefix", models.TextField(unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("is_archived", models.BooleanField(default=False)),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                             related_name="classes", to="account.school")),
                ("teacher", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                              related_name="classes", to="account.user")),
            ],
            options={
                "db_table": "school_class",
                "ordering": ["-year", "grade", "class_no"],
                "unique_together": {("school", "teacher", "year", "grade", "class_no")},
            },
        ),
        migrations.CreateModel(
            name="ClassMembership",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("number", models.IntegerField()),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("school_class", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                   related_name="memberships", to="account.schoolclass")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                              related_name="class_memberships", to="account.user")),
            ],
            options={
                "db_table": "class_membership",
                "ordering": ["number"],
                "unique_together": {("school_class", "number"), ("school_class", "student")},
            },
        ),
    ]
