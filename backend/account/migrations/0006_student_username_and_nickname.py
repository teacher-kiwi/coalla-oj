import secrets

from django.db import migrations, models

PREFIX = "학생"
DIGITS = 8


def _regenerate(apps, schema_editor):
    """학생 아이디를 무작위로 다시 발급하고 닉네임을 채운다.

    옛 아이디는 "c{학급id}-{번호}" 라 공개 화면에 나가면 같은 학급 학생이 묶이고
    번호 순서까지 드러났다. 새 아이디는 아무것도 담지 않는다.

    Submission 은 user 를 FK 로 들고 있어 아이디를 바꿔도 따라올 것이 없다.
    """
    User = apps.get_model("account", "User")
    ClassMembership = apps.get_model("account", "ClassMembership")

    taken = set(User.objects.values_list("username", flat=True))
    upper = 10 ** DIGITS

    memberships = ClassMembership.objects.select_related("student").all()
    for membership in memberships:
        while True:
            candidate = f"{PREFIX}{secrets.randbelow(upper):0{DIGITS}d}"
            if candidate not in taken:
                break
        taken.add(candidate)

        student = membership.student
        taken.discard(student.username)
        student.username = candidate
        student.save(update_fields=["username"])

        membership.nickname = f"{PREFIX}{membership.number}"
        membership.save(update_fields=["nickname"])


def _noop(apps, schema_editor):
    """되돌려도 옛 아이디는 복원할 수 없다(학급 id 와 번호로 다시 만들어야 한다).

    배포 전 단계라 되돌릴 일이 없다고 보고 아이디는 그대로 둔다.
    """


class Migration(migrations.Migration):
    """학생 아이디 무작위화, 학급 소속 닉네임 신설, 실명 폐기."""

    dependencies = [
        ("account", "0005_drop_password_reset"),
    ]

    operations = [
        migrations.AddField(
            model_name="classmembership",
            name="nickname",
            # 기존 행을 채우려면 기본값이 필요하다. 채운 뒤 아래에서 걷어낸다.
            field=models.TextField(default=""),
            preserve_default=False,
        ),
        migrations.RunPython(_regenerate, _noop),
        migrations.RemoveField(model_name="userprofile", name="real_name"),
    ]
