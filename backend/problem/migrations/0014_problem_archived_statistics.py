from django.db import migrations, models

import utils.models


def backfill_archived(apps, schema_editor):
    """이미 지워진 학생들의 몫을 보존 칸으로 옮긴다.

    지금까지 학급을 지워도 통계는 다시 세지 않았다. 그래서 submission_number 에는
    이미 사라진 제출의 몫이 들어 있다. 그대로 두면 이 문제를 처음 재채점하는
    순간 살아 있는 제출만으로 다시 세어져 그 몫이 사라진다.

    "카운터에 있지만 지금 제출로 설명되지 않는 만큼"이 곧 보존해야 할 값이다.
    집계에 넣지 않는 제출(대회 관리자의 시험 제출, 대회 시간 밖 제출)은
    애초에 카운터에 들어가지 않았으므로 여기서도 빼고 센다.
    """
    Problem = apps.get_model("problem", "Problem")
    Submission = apps.get_model("submission", "Submission")
    SUPER_ADMIN = "Super Admin"

    live = {}
    submissions = (Submission.objects.select_related("contest", "user")
                   .only("problem_id", "result", "create_time",
                         "contest__start_time", "contest__end_time", "contest__created_by_id",
                         "user__admin_type"))
    for submission in submissions.iterator():
        contest = submission.contest
        if contest is not None:
            user = submission.user
            if user.admin_type == SUPER_ADMIN or contest.created_by_id == user.id:
                continue
            if not (contest.start_time <= submission.create_time <= contest.end_time):
                continue
        counters = live.setdefault(submission.problem_id, {"n": 0, "ac": 0, "info": {}})
        counters["n"] += 1
        if submission.result == 0:      # JudgeStatus.ACCEPTED
            counters["ac"] += 1
        key = str(submission.result)
        counters["info"][key] = counters["info"].get(key, 0) + 1

    changed = []
    for problem in Problem.objects.all():
        counters = live.get(problem.id, {"n": 0, "ac": 0, "info": {}})
        archived_info = {}
        for key, value in (problem.statistic_info or {}).items():
            left = value - counters["info"].get(str(key), 0)
            if left > 0:
                archived_info[str(key)] = left
        problem.archived_submission_number = max(0, problem.submission_number - counters["n"])
        problem.archived_accepted_number = max(0, problem.accepted_number - counters["ac"])
        problem.archived_statistic_info = archived_info
        changed.append(problem)
    Problem.objects.bulk_update(changed, ["archived_submission_number",
                                          "archived_accepted_number",
                                          "archived_statistic_info"])


class Migration(migrations.Migration):
    """지워진 학생들이 남긴 정답률 몫을 따로 보존한다."""

    dependencies = [
        ("problem", "0013_problem_favorite"),
        ("submission", "0003_drop_shared"),
    ]

    operations = [
        migrations.AddField(
            model_name="problem",
            name="archived_submission_number",
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="problem",
            name="archived_accepted_number",
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="problem",
            name="archived_statistic_info",
            field=utils.models.JSONField(default=dict),
        ),
        migrations.RunPython(backfill_archived, migrations.RunPython.noop),
    ]
