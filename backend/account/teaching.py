"""교사 계정에 딸린 교육용 데이터를 세고 지운다.

교사 계정에는 두 종류의 데이터가 섞여 있다.

- 교육용: 학급, 그 학급의 학생 계정, 문제집, 학급 대회, 비공개(승인대기 포함) 문제,
  바로 과제. 교사가 아니게 되는 순간 아무도 손댈 수 없어진다.
- 일반: 본인이 푼 제출 기록, 프로필처럼 일반 사용자도 갖는 것.
  교사 권한과 무관하므로 건드리지 않는다.

공개 문제는 남긴다. 다른 학급이 이미 풀고 있을 수 있어서, 출제자가 사라진다고
문제까지 없애면 안 된다(Problem.created_by 가 SET_NULL 인 이유다).

교사 기능을 회수할 때는 둘 중 하나를 고른다. 기본은 다른 교사에게 넘기기
(transfer_teaching_data)이고, 지우기(purge_teaching_data)도 할 수 있다.
삭제는 되돌릴 수 없으므로 세는 것과 지우는 것을 나눠 두고, 화면이 먼저 보여준
뒤 지우게 한다.
"""
from django.db import transaction
from django.db.models import Max, Q

from contest.models import Contest, ContestAnnouncement
from homework.models import Homework
from judge.recompute import preserve_statistics
from problem.models import Problem, ProblemSet, ProblemVisibility
from submission.models import Submission
from .models import AdminType, ClassMembership, SchoolClass, User

# 교사가 만든 문제 중 함께 지울 것. 공개 문제는 제외한다.
_OWNED_VISIBILITY = (ProblemVisibility.private, ProblemVisibility.pending)


def teacher_accounts():
    """지금 교사 기능이 있는 계정. User.is_teacher() 와 같은 기준이다."""
    return User.objects.filter(Q(admin_type=AdminType.TEACHER)
                               | Q(admin_type=AdminType.ADMIN, teacher_permission=True))


def _owned_contests(teacher):
    return Contest.objects.filter(created_by=teacher, is_class_contest=True)


def _owned_problems(teacher):
    """교사와 함께 지울 문제.

    남의 대회에 담긴 문제는 남긴다. 그 대회의 제출과 순위가 매달려 있어서
    지울 수 없다(ContestProblem 이 PROTECT 다). 자기 대회에 담긴 것은 대회를
    먼저 지우므로 함께 사라진다.
    """
    in_others_contest = (Q(contest_entries__isnull=False)
                         & ~Q(contest_entries__contest__created_by=teacher))
    return Problem.objects.filter(created_by=teacher, visibility__in=_OWNED_VISIBILITY) \
                          .exclude(in_others_contest).distinct()


def _student_ids(teacher):
    return ClassMembership.objects.filter(school_class__teacher=teacher) \
                                  .values_list("student_id", flat=True)


def teaching_data_summary(teacher):
    """지워질 교육용 데이터의 개수. 값이 모두 0 이면 정리할 것이 없다."""
    student_ids = list(_student_ids(teacher))
    return {
        "class_count": SchoolClass.objects.filter(teacher=teacher).count(),
        "student_count": len(set(student_ids)),
        "student_submission_count": Submission.objects.filter(user_id__in=student_ids).count(),
        "problem_set_count": ProblemSet.objects.filter(created_by=teacher).count(),
        "contest_count": _owned_contests(teacher).count(),
        "private_problem_count": _owned_problems(teacher).count(),
        "homework_count": Homework.objects.filter(created_by=teacher).count(),
    }


def has_teaching_data(teacher):
    return any(teaching_data_summary(teacher).values())


@transaction.atomic
def purge_teaching_data(teacher):
    """교육용 데이터를 지우고 지운 개수를 돌려준다. 계정 자체는 남긴다."""
    summary = teaching_data_summary(teacher)
    student_ids = list(_student_ids(teacher))

    # 바로 과제는 참가자의 임시 계정과 제출까지 함께 지워진다(post_delete 신호).
    # 교사 화면과 달리 진행 중인 과제도 지운다. 남겨 둘 주인이 없기 때문이다.
    Homework.objects.filter(created_by=teacher).delete()
    # 대회를 먼저 지운다. 대회에 담긴 문제는 지울 수 없기 때문이다(PROTECT).
    _owned_contests(teacher).delete()
    # distinct() 가 붙은 쿼리셋은 그대로 delete() 할 수 없어 id 로 다시 부른다
    Problem.objects.filter(
        id__in=list(_owned_problems(teacher).values_list("id", flat=True))).delete()
    ProblemSet.objects.filter(created_by=teacher).delete()
    # 학급을 지우면 소속(ClassMembership)만 사라지고 학생 계정은 남는다.
    # 다른 교사의 학급에도 속한 학생은 그 학급이 남으므로 계정을 지우지 않는다.
    SchoolClass.objects.filter(teacher=teacher).delete()
    _delete_orphan_students(student_ids)
    return summary


def _delete_orphan_students(student_ids):
    """학급이 없어진 학생 계정을 지우고 지운 수를 돌려준다.

    다른 학급에도 속한 학생은 그 학급이 남으므로 지우지 않는다.
    제출이 사라지기 전에 정답률 몫을 문제의 보존 칸으로 옮긴다(preserve_statistics).
    나중에 그 문제를 재채점해도 살아남는다.
    """
    orphans = User.objects.filter(id__in=student_ids, class_memberships__isnull=True)
    count = orphans.count()
    preserve_statistics(Submission.objects.filter(user_id__in=orphans))
    orphans.delete()
    return count


@transaction.atomic
def delete_school_class(school_class):
    """학급과 소속 학생 계정을 지우고, 지운 학생 수를 돌려준다.

    교사의 학급 삭제와 최고관리자의 '수업' 탭이 같이 쓴다.
    """
    student_ids = list(school_class.memberships.values_list("student_id", flat=True))
    school_class.delete()
    return _delete_orphan_students(student_ids)


def transfer_conflicts(source, target):
    """넘기면 겹치는 학급 이름들. 같은 학교·학년도·학년·반을 한 교사가 둘 가질 수 없다."""
    mine = SchoolClass.objects.filter(teacher=source).select_related("school")
    taken = set(SchoolClass.objects.filter(teacher=target)
                .values_list("school_id", "year", "grade", "class_no"))
    return [str(c) for c in mine if (c.school_id, c.year, c.grade, c.class_no) in taken]


@transaction.atomic
def transfer_teaching_data(source, target):
    """source 의 교육용 데이터를 target 교사에게 넘기고, 넘긴 개수를 돌려준다.

    학생 계정·제출·배포는 그대로 두고 주인만 바꾼다. 문제집·대회의 배포가 가리키는
    학급도 함께 넘어가므로 넘긴 뒤에도 서로 어긋나지 않는다. 그래서 학급 하나만
    넘기는 길은 두지 않는다(남의 문제집이 내 학급에 배포된 상태가 생긴다).

    공개 문제는 출제자를 남긴다. 지우기(purge)와 같은 기준이다.
    """
    summary = teaching_data_summary(source)

    # 넘겨받는 교사의 학급 순서 뒤에 원래 순서대로 붙인다
    start = SchoolClass.objects.filter(teacher=target).aggregate(m=Max("order"))["m"] or 0
    classes = list(SchoolClass.objects.filter(teacher=source).order_by("order", "-year", "grade", "class_no"))
    for i, c in enumerate(classes, start=1):
        c.teacher = target
        c.order = start + i
    SchoolClass.objects.bulk_update(classes, ["teacher", "order"])

    contests = _owned_contests(source)
    # 대회 공지도 넘긴다. 남겨 두면 옛 교사 계정을 지울 때 함께 지워진다(CASCADE).
    ContestAnnouncement.objects.filter(contest__in=contests, created_by=source).update(created_by=target)
    contests.update(created_by=target)
    ProblemSet.objects.filter(created_by=source).update(created_by=target)
    # 지우기와 달리 남의 대회에 담긴 비공개 문제도 넘긴다. 넘기는 데는 걸림이 없다.
    Problem.objects.filter(created_by=source, visibility__in=_OWNED_VISIBILITY).update(created_by=target)
    Homework.objects.filter(created_by=source).update(created_by=target)
    return summary
