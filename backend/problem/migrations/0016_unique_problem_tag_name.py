from django.db import migrations, models


def merge_duplicate_tags(apps, schema_editor):
    Problem = apps.get_model("problem", "Problem")
    ProblemTag = apps.get_model("problem", "ProblemTag")

    seen = {}
    for tag in ProblemTag.objects.order_by("id"):
        primary_id = seen.get(tag.name)
        if primary_id is None:
            seen[tag.name] = tag.id
            continue

        primary = ProblemTag.objects.get(id=primary_id)
        for problem in Problem.objects.filter(tags=tag):
            problem.tags.add(primary)
        tag.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("problem", "0015_auto_20260125_1346"),
    ]

    operations = [
        migrations.RunPython(merge_duplicate_tags, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="problemtag",
            name="name",
            field=models.TextField(unique=True),
        ),
    ]
