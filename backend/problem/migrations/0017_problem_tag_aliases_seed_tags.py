from django.db import migrations, models


DEFAULT_TAGS = [
    ("수학", ["math"]),
    ("구현", ["implementation"]),
    ("동적계획법", ["dp", "dynamic_programming"]),
    ("자료 구조", ["data_structures"]),
    ("그래프 이론", ["graphs"]),
    ("그리디 알고리즘", ["greedy"]),
    ("문자열", ["string"]),
    ("브루트포스 알고리즘", ["bruteforcing", "bruteforce"]),
    ("그래프 탐색", ["graph_traversal"]),
    ("정렬", ["sorting", "sort"]),
]


def seed_problem_tags(apps, schema_editor):
    ProblemTag = apps.get_model("problem", "ProblemTag")
    for name, aliases in DEFAULT_TAGS:
        tag, _ = ProblemTag.objects.get_or_create(name=name)
        tag.aliases = aliases
        tag.save(update_fields=["aliases"])


class Migration(migrations.Migration):

    dependencies = [
        ("problem", "0016_unique_problem_tag_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="problemtag",
            name="aliases",
            field=models.JSONField(default=list),
        ),
        migrations.RunPython(seed_problem_tags, migrations.RunPython.noop),
    ]
