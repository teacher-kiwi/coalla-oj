from django.db import migrations


class Migration(migrations.Migration):
    """프로필 사진을 도트 캐릭터로 바꾸면서 사진 경로 칸을 없앤다.

    올라와 있던 사진 파일(/data/public/avatar)은 지우지 않는다.
    """

    dependencies = [
        ("account", "0007_school_class_order"),
    ]

    operations = [
        migrations.RemoveField(model_name="userprofile", name="avatar"),
    ]
