# 교육용 전환 6단계: 제출 공유 제거 (교육용에서는 커닝 통로)
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("submission", "0002_submission_user_fk"),
    ]

    operations = [
        migrations.RemoveField(model_name="submission", name="shared"),
    ]
