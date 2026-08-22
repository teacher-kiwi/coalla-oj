from django.db import migrations


class Migration(migrations.Migration):
    """비밀번호 재설정(메일) 기능 제거에 따른 필드 삭제.

    신규 가입은 구글로만 받고 수업용 학생 계정은 교사가 만들어 주므로,
    스스로 비밀번호를 만드는 경로가 없어 재설정 메일을 보낼 대상이 없었다.
    """

    dependencies = [
        ("account", "0004_drop_profile_fields"),
    ]

    operations = [
        migrations.RemoveField(model_name="user", name="reset_password_token"),
        migrations.RemoveField(model_name="user", name="reset_password_token_expire_time"),
    ]
