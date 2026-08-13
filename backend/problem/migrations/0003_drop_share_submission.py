# 교육용 전환 6단계: 제출 공유 제거에 따른 문제 옵션 정리
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("problem", "0002_problem_set"),
    ]

    operations = [
        migrations.RemoveField(model_name="problem", name="share_submission"),
    ]
