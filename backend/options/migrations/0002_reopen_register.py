# allow_register 의 의미 변경에 따른 정정.
#
# 처음에는 "공개 회원가입 차단" 목적으로 False 로 두었으나,
# 이후 설계가 "일반 회원(교사·개인학생)은 구글로 가입" 으로 바뀌면서
# 이 플래그가 구글 신규 가입을 막는 결과가 되었다.
# 이제 이 값은 "신규 가입(구글) 허용" 을 뜻한다.
from django.db import migrations


def apply(apps, schema_editor):
    SysOptions = apps.get_model("options", "SysOptions")
    SysOptions.objects.update_or_create(key="allow_register", defaults={"value": True})


def revert(apps, schema_editor):
    SysOptions = apps.get_model("options", "SysOptions")
    SysOptions.objects.update_or_create(key="allow_register", defaults={"value": False})


class Migration(migrations.Migration):

    dependencies = [
        ("options", "0001_initial"),
    ]

    operations = [migrations.RunPython(apply, revert)]
