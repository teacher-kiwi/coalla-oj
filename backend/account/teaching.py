"""교사 계정에 딸린 교육용 데이터를 세고 지운다.

교사 계정에는 두 종류의 데이터가 섞여 있다.

- 교육용: 학급, 그 학급의 학생 계정, 문제집, 비공개(승인대기 포함) 문제.
  교사가 아니게 되는 순간 아무도 손댈 수 없어진다.
- 일반: 본인이 푼 제출 기록, 프로필처럼 일반 사용자도 갖는 것.
  교사 권한과 무관하므로 건드리지 않는다.

공개 문제는 남긴다. 다른 학급이 이미 풀고 있을 수 있어서, 출제자가 사라진다고
문제까지 없애면 안 된다(Problem.created_by 가 SET_NULL 인 이유다).

삭제는 되돌릴 수 없으므로 세는 것과 지우는 것을 나눠 두고, 화면이 먼저 보여준
뒤 지우게 한다.
"""
from django.db import transaction

from problem.models import Problem, ProblemSet, ProblemVisibility
from submission.models import Submission
from .models import ClassMembership, SchoolClass, User

# 교사가 만든 문제 중 함께 지울 것. 공개 문제는 제외한다.
_OWNED_VISIBILITY = (ProblemVisibility.private, ProblemVisibility.pending)


def _owned_problems(teacher):
    return Problem.objects.filter(created_by=teacher, contest_id__isnull=True,
                                  visibility__in=_OWNED_VISIBILITY)


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
        "private_problem_count": _owned_problems(teacher).count(),
    }


def has_teaching_data(teacher):
    return any(teaching_data_summary(teacher).values())


@transaction.atomic
def purge_teaching_data(teacher):
    """교육용 데이터를 지우고 지운 개수를 돌려준다. 계정 자체는 남긴다."""
    summary = teaching_data_summary(teacher)
    student_ids = list(_student_ids(teacher))

    _owned_problems(teacher).delete()
    ProblemSet.objects.filter(created_by=teacher).delete()
    # 학급을 지우면 소속(ClassMembership)만 사라지고 학생 계정은 남는다.
    # 다른 교사의 학급에도 속한 학생은 그 학급이 남으므로 계정을 지우지 않는다.
    SchoolClass.objects.filter(teacher=teacher).delete()
    User.objects.filter(id__in=student_ids, class_memberships__isnull=True).delete()
    return summary
