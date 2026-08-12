# Submission 을 User FK 로 전환한다.
#
# 원본은 user_id(IntegerField) + username(문자열 복사본) 구조였다.
# 조인 비용을 피하려는 설계였지만, 이 규모(연간 수만 건)에서는 의미가 없고
# 닉네임을 바꿔도 과거 기록에 반영되지 않는 문제가 있었다.
#
# 주의: submission 테이블이 비어 있어야 한다(non-null FK 추가).
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0002_school_class_membership"),
        ("submission", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(model_name="submission", name="username"),
        migrations.RemoveField(model_name="submission", name="user_id"),
        migrations.AddField(
            model_name="submission",
            name="user",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                    related_name="submissions", to="account.user",
                                    default=None, null=False),
            preserve_default=False,
        ),
    ]
