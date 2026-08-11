# 2단계 인증(TOTP)과 OpenAPI appkey 기능을 제거하면서 관련 컬럼을 정리한다.
# 두 기능 모두 실사용 계정이 0명이라 데이터 이관은 필요 없다.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0013_auto_20260125_1346"),
    ]

    operations = [
        migrations.RemoveField(model_name="user", name="two_factor_auth"),
        migrations.RemoveField(model_name="user", name="tfa_token"),
        migrations.RemoveField(model_name="user", name="open_api"),
        migrations.RemoveField(model_name="user", name="open_api_appkey"),
    ]
