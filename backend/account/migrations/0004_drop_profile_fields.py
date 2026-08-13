# 교육용 전환 6단계: 쓰지 않는 프로필 필드 제거 (계획서 7장)
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0003_drop_username_prefix"),
    ]

    operations = [
        migrations.RemoveField(model_name="userprofile", name="blog"),
        migrations.RemoveField(model_name="userprofile", name="mood"),
        migrations.RemoveField(model_name="userprofile", name="github"),
        migrations.RemoveField(model_name="userprofile", name="school"),
        migrations.RemoveField(model_name="userprofile", name="major"),
        migrations.RemoveField(model_name="userprofile", name="language"),
    ]
