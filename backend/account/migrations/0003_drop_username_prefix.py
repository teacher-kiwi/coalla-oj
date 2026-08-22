# 학생 계정 아이디 접두사를 교사가 직접 정하게 하던 것을 없앤다.
#
# 아이디는 교사도 학생도 입력하지 않는 내부 값인데, 전역 유일한 접두사를
# 사람이 만들게 하면서 "이미 사용 중" 오류가 나는 불필요한 마찰이 있었다.
# 이제 학급 id 로 "c{학급id}-{번호}" 형태를 만든다.
# (이 형태는 0006 에서 다시 무작위 "학생12345678" 로 바뀐다. 공개 화면에 아이디가
#  그대로 나가면서 학급과 번호가 드러났기 때문이다.)
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0002_school_class_membership"),
    ]

    operations = [
        migrations.RemoveField(model_name="schoolclass", name="username_prefix"),
    ]
