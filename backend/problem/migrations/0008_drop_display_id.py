# 공개 문제의 표시 번호(_id)를 없애고 pk 를 그대로 번호로 쓴다.
#
# _id 는 "지금까지 쓴 것 중 가장 큰 값 + 1" 로 매겼다. 읽고 쓰는 사이에 다른
# 요청이 끼어들면 같은 번호가 둘 생겨서, 중복을 막는 부분 인덱스와 재시도가
# 붙어 있었다. 문자열이라 정렬도 길이를 먼저 보는 식이었다. pk 는 DB 가
# 겹치지 않게 발급하므로 그 장치들이 전부 필요 없어진다.
#
# 주소가 바뀐다(/problem/1000 -> /problem/42). 배포 전이라 그대로 간다.
from django.db import migrations, models


def drop_display_id_copy(apps, schema_editor):
    """프로필에 사본으로 넣어둔 표시 번호를 지운다.

    {"problems": {"42": {"status": 0, "_id": "1000"}}} 에서 키가 곧 번호가 되어
    _id 가 중복이다. 사본을 갱신하던 API 도 함께 없앴다.
    """
    UserProfile = apps.get_model("account", "UserProfile")
    for profile in UserProfile.objects.only("id", "acm_problems_status",
                                            "oi_problems_status").iterator():
        changed = False
        for status in (profile.acm_problems_status, profile.oi_problems_status):
            for group in status.values():
                if not isinstance(group, dict):
                    continue
                for entry in group.values():
                    if isinstance(entry, dict) and entry.pop("_id", None) is not None:
                        changed = True
        if changed:
            profile.save(update_fields=["acm_problems_status", "oi_problems_status"])


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0006_student_username_and_nickname"),
        ("problem", "0007_contest_problem_order"),
    ]

    operations = [
        migrations.RunPython(drop_display_id_copy, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="problem",
            name="uniq_public_display_id",
        ),
        migrations.RemoveField(
            model_name="problem",
            name="_id",
        ),
        migrations.AlterModelOptions(
            name="problem",
            options={"ordering": ("order", "id")},
        ),
    ]
