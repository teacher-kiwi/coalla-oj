# 프로필의 대회 안 현황을 대회별로 나눈다.
#
# 예전에는 대회 문제가 복사본이라 문제 id 만으로 담아도 대회끼리 섞이지 않았다.
# 이제 한 문제를 여러 대회에 담을 수 있어, 문제 id 만 보면 대회 A 에서 푼 것이
# 대회 B 에서도 풀린 것으로 보인다.
#
# 옛 값은 문제 id 를 키로 갖는데 새 코드는 그 자리를 대회 id 로 읽는다. 그대로
# 두면 엉뚱한 대회의 현황이 되므로 비운다. 순위표(ACMContestRank)가 따로 있어
# 대회 결과 자체는 남는다.
from django.db import migrations


def clear_contest_problem_status(apps, schema_editor):
    UserProfile = apps.get_model("account", "UserProfile")
    for profile in UserProfile.objects.only("id", "acm_problems_status",
                                            "oi_problems_status").iterator():
        changed = False
        for status in (profile.acm_problems_status, profile.oi_problems_status):
            if status.pop("contest_problems", None) is not None:
                changed = True
        if changed:
            profile.save(update_fields=["acm_problems_status", "oi_problems_status"])


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0006_student_username_and_nickname"),
        ("problem", "0009_contest_problem"),
    ]

    operations = [
        migrations.RunPython(clear_contest_problem_status, migrations.RunPython.noop),
    ]
