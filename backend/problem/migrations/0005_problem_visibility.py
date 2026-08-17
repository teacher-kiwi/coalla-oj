from django.db import migrations, models
import django.db.models.deletion
import django.db.models.functions


class Migration(migrations.Migration):
    """공개 범위 필드 추가와 출제자 삭제 규칙 변경.

    - visibility: 기존 문제는 모두 관리자가 만든 공개 문제라 public 으로 둔다.
    - created_by: CASCADE 였다. 출제자를 지우면 문제와 그 제출 기록까지 사라져서
      공개 문제가 통째로 날아갈 수 있었다. SET_NULL 로 바꿔 문제를 남긴다.
    """

    dependencies = [
        ("problem", "0004_difficulty_six_levels"),
        ("account", "0004_drop_profile_fields"),
    ]

    operations = [
        # 표시 번호가 문자열이라 길이를 먼저 보고 정렬한다(2 가 12 보다 앞에 오도록)
        migrations.AlterModelOptions(
            name="problem",
            options={"ordering": (django.db.models.functions.Length("_id"), "_id")},
        ),
        migrations.AddField(
            model_name="problem",
            name="visibility",
            field=models.TextField(default="public"),
        ),
        migrations.AlterField(
            model_name="problem",
            name="created_by",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    to="account.user"),
        ),
    ]
