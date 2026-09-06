"""테스트케이스를 고친 뒤 다시 채점하고 집계를 다시 만드는 부분.

채점 서버를 부르지 않고, 다시 채점하면 결과가 이렇게 바뀐다고 정해놓고 검증한다.
검증 대상은 "바뀐 결과에서 파생된 값이 제대로 다시 만들어지는가"다.
"""
from copy import deepcopy
from datetime import timedelta
from unittest import mock

from django.utils.timezone import now

from account.models import User
from contest.models import ACMContestRank, Contest, OIContestRank
from problem.models import ContestProblem, Problem, ProblemRuleType
from submission.models import JudgeStatus, Submission
from utils.api.tests import APITestCase
from utils.constants import ContestRuleType

from .recompute import preserve_statistics, rebuild_after_rejudge, rebuild_contest_rank
from .rejudge import rejudge_problem
from .tests import DEFAULT_PROBLEM_DATA


class ActorRegistrationTest(APITestCase):
    """액터가 워커에 등록되는지.

    워커는 "tasks" 라는 이름의 모듈만 훑는다. 다른 파일에 두면 보낸 작업이
    ActorNotFound 로 버려지는데, 화면에는 아무 오류도 나지 않아 조용히 실패한다.
    """
    def test_actors_are_defined_in_the_module_the_worker_scans(self):
        import dramatiq
        from django.conf import settings

        # 웹 프로세스는 뷰를 거쳐 어느 모듈이든 불러오므로 여기서 액터를 찾을 수
        # 있다는 것만으로는 부족하다. 워커가 훑는 이름으로 정의됐는지를 본다.
        scanned = getattr(settings, "DRAMATIQ_AUTODISCOVER_MODULES", ("tasks",))
        broker = dramatiq.get_broker()
        for actor_name in ("judge_task", "rejudge_problem_task", "delete_files"):
            actor = broker.get_actor(actor_name)
            module = actor.fn.__module__.rsplit(".", 1)[-1]
            self.assertIn(module, scanned,
                          f"{actor_name} 는 {actor.fn.__module__} 에 있어 워커가 찾지 못한다")


class RecomputeTestBase(APITestCase):
    def setUp(self):
        self.admin = self.create_admin("teacher", "test123", login=False)
        self.problem = self._problem()
        self.students = [self.create_user(f"student{i}", "test123", login=False)
                         for i in range(3)]

    def _problem(self, **overrides):
        data = deepcopy(DEFAULT_PROBLEM_DATA)
        data.update(overrides)
        data["created_by"] = self.admin
        return Problem.objects.create(**data)

    def _contest(self, rule_type=ContestRuleType.ACM, started_ago=timedelta(hours=2)):
        contest = Contest.objects.create(
            title="c", description="d", rule_type=rule_type, real_time_rank=True,
            start_time=now() - started_ago, end_time=now() + timedelta(hours=1),
            created_by=self.admin)
        ContestProblem.objects.create(contest=contest, problem=self.problem, order=1)
        return contest

    def _submit(self, user, result, contest=None, minutes=0, score=None):
        """제출을 만든다. create_time 은 auto_now_add 라 만든 뒤에 고쳐 넣는다."""
        info = {"score": score} if score is not None else {}
        submission = Submission.objects.create(
            problem=self.problem, contest=contest, user=user, code="x",
            language="C", result=result, statistic_info=info)
        moment = now() + timedelta(minutes=minutes)
        Submission.objects.filter(id=submission.id).update(create_time=moment)
        submission.refresh_from_db()
        return submission


class ProblemStatisticsRebuildTest(RecomputeTestBase):
    def test_counters_come_from_the_submissions(self):
        self._submit(self.students[0], JudgeStatus.ACCEPTED)
        self._submit(self.students[1], JudgeStatus.WRONG_ANSWER)
        self._submit(self.students[1], JudgeStatus.ACCEPTED)
        # 엉뚱한 값이 들어 있어도 다시 세면 맞아야 한다
        Problem.objects.filter(id=self.problem.id).update(
            submission_number=99, accepted_number=99, statistic_info={"0": 99})

        rebuild_after_rejudge(self.problem)

        problem = Problem.objects.get(id=self.problem.id)
        self.assertEqual(problem.submission_number, 3)
        self.assertEqual(problem.accepted_number, 2)
        self.assertEqual(problem.statistic_info,
                         {str(JudgeStatus.ACCEPTED): 2, str(JudgeStatus.WRONG_ANSWER): 1})

    def test_deleted_students_are_kept_through_a_rejudge(self):
        """학년이 끝나 학생을 지워도 "몇 명이 도전해 몇 번 맞혔나" 는 남아야 한다.

        지우기 직전에 몫을 옮겨 두지 않으면, 그 문제를 다시 채점하는 순간
        살아 있는 제출만으로 다시 세어져 예전 기록이 사라진다.
        """
        leaving = self.students[0]
        self._submit(leaving, JudgeStatus.WRONG_ANSWER)
        self._submit(leaving, JudgeStatus.ACCEPTED)
        self._submit(self.students[1], JudgeStatus.ACCEPTED)
        rebuild_after_rejudge(self.problem)
        self.assertEqual(Problem.objects.get(id=self.problem.id).submission_number, 3)

        # 학년 종료: 제출을 지우기 전에 몫을 옮기고 계정을 지운다
        preserve_statistics(Submission.objects.filter(user=leaving))
        leaving.delete()

        problem = Problem.objects.get(id=self.problem.id)
        self.assertEqual(problem.archived_submission_number, 2)
        self.assertEqual(problem.archived_accepted_number, 1)

        # 나중에 테스트케이스를 고쳐 다시 채점해도 그 몫이 살아 있어야 한다
        rebuild_after_rejudge(self.problem)
        problem = Problem.objects.get(id=self.problem.id)
        self.assertEqual(problem.submission_number, 3)
        self.assertEqual(problem.accepted_number, 2)
        self.assertEqual(problem.statistic_info,
                         {str(JudgeStatus.ACCEPTED): 2, str(JudgeStatus.WRONG_ANSWER): 1})

    def test_preserving_twice_adds_up(self):
        """해마다 학급을 지운다. 지울 때마다 쌓여야 한다."""
        for student in self.students[:2]:
            self._submit(student, JudgeStatus.ACCEPTED)
            preserve_statistics(Submission.objects.filter(user=student))
            student.delete()

        problem = Problem.objects.get(id=self.problem.id)
        self.assertEqual(problem.archived_submission_number, 2)
        self.assertEqual(problem.archived_accepted_number, 2)
        self.assertEqual(problem.archived_statistic_info, {str(JudgeStatus.ACCEPTED): 2})

    def test_contest_admin_submissions_are_not_preserved(self):
        """통계에 넣지 않는 제출은 보존 칸에도 들어가면 안 된다(두 번 세어진다)."""
        contest = self._contest()
        self._submit(self.admin, JudgeStatus.ACCEPTED, contest=contest)

        preserve_statistics(Submission.objects.filter(user=self.admin))

        problem = Problem.objects.get(id=self.problem.id)
        self.assertEqual(problem.archived_submission_number, 0)
        self.assertEqual(problem.archived_statistic_info, {})

    def test_contest_counters_do_not_keep_deleted_students(self):
        """대회별 통계는 보존하지 않는다. 학생이 지워지면 순위 행도 함께 사라져,
        남아 있는 제출만 보여주는 쪽이 순위표와 앞뒤가 맞는다."""
        contest = self._contest()
        leaving = self.students[0]
        self._submit(leaving, JudgeStatus.ACCEPTED, contest=contest)
        self._submit(self.students[1], JudgeStatus.ACCEPTED, contest=contest)

        preserve_statistics(Submission.objects.filter(user=leaving))
        leaving.delete()
        rebuild_after_rejudge(self.problem)

        entry = ContestProblem.objects.get(contest=contest, problem=self.problem)
        self.assertEqual(entry.submission_number, 1)
        # 문제 쪽은 지워진 몫까지 합쳐 둘이다
        self.assertEqual(Problem.objects.get(id=self.problem.id).submission_number, 2)

    def test_contest_counters_are_separate_from_the_lifetime_total(self):
        contest = self._contest()
        self._submit(self.students[0], JudgeStatus.ACCEPTED)                    # 대회 밖
        self._submit(self.students[1], JudgeStatus.ACCEPTED, contest=contest)   # 대회 안

        rebuild_after_rejudge(self.problem)

        self.assertEqual(Problem.objects.get(id=self.problem.id).submission_number, 2)
        entry = ContestProblem.objects.get(contest=contest, problem=self.problem)
        self.assertEqual(entry.submission_number, 1)
        self.assertEqual(entry.accepted_number, 1)

    def test_contest_admin_submissions_are_not_counted(self):
        """자기 대회에 미리 넣어보는 시험 제출은 통계에 넣지 않는다."""
        contest = self._contest()
        self._submit(self.admin, JudgeStatus.ACCEPTED, contest=contest)

        rebuild_after_rejudge(self.problem)

        self.assertEqual(Problem.objects.get(id=self.problem.id).submission_number, 0)
        entry = ContestProblem.objects.get(contest=contest, problem=self.problem)
        self.assertEqual(entry.submission_number, 0)

    def test_submissions_outside_the_contest_window_are_not_counted(self):
        contest = self._contest()
        self._submit(self.students[0], JudgeStatus.ACCEPTED, contest=contest, minutes=120)

        rebuild_after_rejudge(self.problem)

        entry = ContestProblem.objects.get(contest=contest, problem=self.problem)
        self.assertEqual(entry.submission_number, 0)


class ACMRankRebuildTest(RecomputeTestBase):
    def test_penalty_counts_only_wrong_answers_before_the_accepted_one(self):
        contest = self._contest()
        student = self.students[0]
        self._submit(student, JudgeStatus.WRONG_ANSWER, contest=contest, minutes=-90)
        self._submit(student, JudgeStatus.COMPILE_ERROR, contest=contest, minutes=-80)
        self._submit(student, JudgeStatus.ACCEPTED, contest=contest, minutes=-70)
        # 맞힌 뒤의 제출은 세지 않는다
        self._submit(student, JudgeStatus.WRONG_ANSWER, contest=contest, minutes=-60)

        rebuild_contest_rank(contest)

        rank = ACMContestRank.objects.get(contest=contest, user=student)
        self.assertEqual(rank.accepted_number, 1)
        self.assertEqual(rank.submission_number, 3)
        info = rank.submission_info[str(self.problem.id)]
        self.assertTrue(info["is_ac"])
        # 컴파일 에러는 패널티가 없으므로 오답 한 번만 센다
        self.assertEqual(info["error_number"], 1)
        # ac_time 은 초 단위 실수고 total_time 은 정수 칸이라 저장하며 잘린다
        self.assertEqual(rank.total_time, int(info["ac_time"] + 20 * 60))

    def test_first_ac_goes_to_the_earliest(self):
        contest = self._contest()
        self._submit(self.students[0], JudgeStatus.ACCEPTED, contest=contest, minutes=-90)
        self._submit(self.students[1], JudgeStatus.ACCEPTED, contest=contest, minutes=-60)

        rebuild_contest_rank(contest)

        key = str(self.problem.id)
        first = ACMContestRank.objects.get(contest=contest, user=self.students[0])
        second = ACMContestRank.objects.get(contest=contest, user=self.students[1])
        self.assertTrue(first.submission_info[key]["is_first_ac"])
        self.assertFalse(second.submission_info[key]["is_first_ac"])

    def test_stale_rank_rows_are_replaced(self):
        """옛 순위가 남아 있으면 안 된다. 통째로 지우고 다시 쌓는다."""
        contest = self._contest()
        ACMContestRank.objects.create(contest=contest, user=self.students[0],
                                      accepted_number=7, total_time=999,
                                      submission_number=7, submission_info={"999": {}})
        self._submit(self.students[0], JudgeStatus.WRONG_ANSWER, contest=contest, minutes=-30)

        rebuild_contest_rank(contest)

        rank = ACMContestRank.objects.get(contest=contest, user=self.students[0])
        self.assertEqual(rank.accepted_number, 0)
        self.assertEqual(rank.total_time, 0)
        self.assertEqual(list(rank.submission_info), [str(self.problem.id)])

    def test_a_user_with_no_counted_submission_leaves_no_row(self):
        contest = self._contest()
        ACMContestRank.objects.create(contest=contest, user=self.students[0])

        rebuild_contest_rank(contest)

        self.assertFalse(ACMContestRank.objects.filter(contest=contest).exists())


class OIRankRebuildTest(RecomputeTestBase):
    def setUp(self):
        super().setUp()
        self.problem.rule_type = ProblemRuleType.OI
        self.problem.save(update_fields=["rule_type"])

    def test_last_submission_score_wins(self):
        contest = self._contest(rule_type=ContestRuleType.OI)
        student = self.students[0]
        self._submit(student, JudgeStatus.PARTIALLY_ACCEPTED, contest=contest,
                     minutes=-90, score=40)
        self._submit(student, JudgeStatus.ACCEPTED, contest=contest, minutes=-60, score=100)

        rebuild_contest_rank(contest)

        rank = OIContestRank.objects.get(contest=contest, user=student)
        self.assertEqual(rank.total_score, 100)
        self.assertEqual(rank.submission_info[str(self.problem.id)], 100)

    def test_a_lower_later_score_replaces_the_higher_one(self):
        """마지막 제출이 기준이다. 최고점을 남기지 않는다."""
        contest = self._contest(rule_type=ContestRuleType.OI)
        student = self.students[0]
        self._submit(student, JudgeStatus.ACCEPTED, contest=contest, minutes=-90, score=100)
        self._submit(student, JudgeStatus.PARTIALLY_ACCEPTED, contest=contest,
                     minutes=-60, score=30)

        rebuild_contest_rank(contest)

        self.assertEqual(OIContestRank.objects.get(contest=contest, user=student).total_score, 30)


class SolvedStatusRebuildTest(RecomputeTestBase):
    def _profile(self, user):
        return User.objects.get(id=user.id).userprofile

    def test_accepted_becomes_wrong_after_rejudge(self):
        """테스트케이스를 고쳐 정답이 오답이 되면 푼 문제 표시도 사라져야 한다."""
        student = self.students[0]
        submission = self._submit(student, JudgeStatus.ACCEPTED)
        profile = self._profile(student)
        profile.acm_problems_status = {"problems": {str(self.problem.id): {"status": 0}}}
        profile.accepted_number = 1
        profile.save()

        Submission.objects.filter(id=submission.id).update(result=JudgeStatus.WRONG_ANSWER)
        rebuild_after_rejudge(self.problem)

        profile = self._profile(student)
        self.assertEqual(profile.acm_problems_status["problems"][str(self.problem.id)],
                         {"status": JudgeStatus.WRONG_ANSWER})
        self.assertEqual(profile.accepted_number, 0)

    def test_wrong_becomes_accepted_after_rejudge(self):
        student = self.students[0]
        submission = self._submit(student, JudgeStatus.WRONG_ANSWER)
        Submission.objects.filter(id=submission.id).update(result=JudgeStatus.ACCEPTED)

        rebuild_after_rejudge(self.problem)

        profile = self._profile(student)
        self.assertEqual(profile.acm_problems_status["problems"][str(self.problem.id)],
                         {"status": JudgeStatus.ACCEPTED})
        self.assertEqual(profile.accepted_number, 1)
        self.assertEqual(profile.submission_number, 1)

    def test_other_problems_are_left_alone(self):
        """이 문제 몫만 고친다. 다른 문제로 세어둔 값이 깎이면 안 된다."""
        student = self.students[0]
        other = self._problem()
        self._submit(student, JudgeStatus.WRONG_ANSWER)
        Submission.objects.create(problem=other, user=student, code="x", language="C",
                                  result=JudgeStatus.ACCEPTED)
        profile = self._profile(student)
        profile.acm_problems_status = {"problems": {str(other.id): {"status": 0}}}
        profile.save()

        rebuild_after_rejudge(self.problem)

        profile = self._profile(student)
        self.assertEqual(profile.acm_problems_status["problems"][str(other.id)]["status"], 0)
        self.assertEqual(profile.accepted_number, 1)
        self.assertEqual(profile.submission_number, 2)

    def test_contest_solve_marks_the_problem_solved(self):
        contest = self._contest()
        self._submit(self.students[0], JudgeStatus.ACCEPTED, contest=contest, minutes=-30)

        rebuild_after_rejudge(self.problem)

        profile = self._profile(self.students[0])
        self.assertEqual(profile.acm_problems_status["problems"][str(self.problem.id)],
                         {"status": JudgeStatus.ACCEPTED})


class RejudgeProblemTest(RecomputeTestBase):
    """다시 채점하는 흐름. 채점 서버는 부르지 않고 결과만 정해준다."""
    def test_every_submission_is_rejudged_without_touching_stats_midway(self):
        contest = self._contest()
        for student in self.students:
            self._submit(student, JudgeStatus.WRONG_ANSWER, contest=contest, minutes=-30)

        def pretend_accepted(dispatcher, update_stats=True):
            # 다시 채점하는 동안에는 통계를 건드리지 않아야 한다
            self.assertFalse(update_stats)
            Submission.objects.filter(id=dispatcher.submission.id).update(
                result=JudgeStatus.ACCEPTED)
            return True

        with mock.patch("judge.dispatcher.JudgeDispatcher.judge", pretend_accepted):
            count = rejudge_problem(self.problem)

        self.assertEqual(count, 3)
        self.assertEqual(Problem.objects.get(id=self.problem.id).accepted_number, 3)
        self.assertEqual(ACMContestRank.objects.filter(contest=contest,
                                                       accepted_number=1).count(), 3)

    def test_waits_and_retries_while_no_judge_server_is_free(self):
        self._submit(self.students[0], JudgeStatus.WRONG_ANSWER)
        attempts = []

        def busy_twice(dispatcher, update_stats=True):
            attempts.append(1)
            return len(attempts) > 2

        with mock.patch("judge.dispatcher.JudgeDispatcher.judge", busy_twice):
            count = rejudge_problem(self.problem, sleep=lambda seconds: None)

        self.assertEqual(count, 1)
        self.assertEqual(len(attempts), 3)

    def test_gives_up_instead_of_waiting_forever(self):
        self._submit(self.students[0], JudgeStatus.WRONG_ANSWER)

        with mock.patch("judge.dispatcher.JudgeDispatcher.judge", lambda *a, **k: False):
            count = rejudge_problem(self.problem, sleep=lambda seconds: None)

        # 채점하지 못했어도 집계는 남은 결과로 다시 만들어 앞뒤가 맞게 둔다
        self.assertEqual(count, 0)
        self.assertEqual(Problem.objects.get(id=self.problem.id).submission_number, 1)
