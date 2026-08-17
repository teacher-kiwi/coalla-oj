from django.db import migrations

# 3단계(Low/Mid/High) 를 6단계(L1~L6) 로 옮긴다.
# 기존 문제는 아래쪽 세 단계(입문·기초·기본)로 보낸다.
FORWARD = {"Low": "L1", "Mid": "L2", "High": "L3"}
BACKWARD = {v: k for k, v in FORWARD.items()}


def convert(apps, mapping, fallback):
    Problem = apps.get_model("problem", "Problem")
    for old, new in mapping.items():
        Problem.objects.filter(difficulty=old).update(difficulty=new)
    # 매핑에 없는 값(직접 넣은 값 등)은 가운데 단계로 모은다
    Problem.objects.exclude(difficulty__in=mapping.values()).update(difficulty=fallback)


def forwards(apps, schema_editor):
    convert(apps, FORWARD, "L2")


def backwards(apps, schema_editor):
    convert(apps, BACKWARD, "Mid")


class Migration(migrations.Migration):
    dependencies = [("problem", "0003_drop_share_submission")]
    operations = [migrations.RunPython(forwards, backwards)]
