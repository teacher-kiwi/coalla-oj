"""교사 전용 문제집 API (/api/teacher/problem_set*).

교사는 `is_admin_role()` 에서 제외되어 있어 /api/admin/* 을 쓸 수 없다.
여기의 모든 조회·수정은 "내가 만든 문제집"과 "내가 담당하는 학급"으로 범위를 좁힌다.
"""
from django.db import IntegrityError, transaction
from django.db.models import Count, Max

from account.decorators import teacher_required
from account.views.teacher import owned_class
from utils.api import APIView, validate_serializer

from ..models import Problem, ProblemSet, ProblemSetAssignment, ProblemSetItem
from ..serializers import (CreateProblemSetAssignmentSerializer, CreateProblemSetSerializer,
                           EditProblemSetAssignmentSerializer, EditProblemSetSerializer,
                           ProblemSetDetailSerializer, ProblemSetItemOrderSerializer,
                           ProblemSetProblemSerializer, ProblemSetSerializer)


def owned_problem_set(user, problem_set_id):
    """내가 만든 문제집만 돌려준다. 아니면 None.

    최고관리자는 운영·점검을 위해 통과시킨다(`owned_class` 와 같은 규칙).
    """
    problem_set_id = int_or_none(problem_set_id)
    if problem_set_id is None:
        return None
    qs = ProblemSet.objects.all()
    if user.is_super_admin():
        return qs.filter(id=problem_set_id).first()
    return qs.filter(id=problem_set_id, created_by=user).first()


def int_or_none(value):
    """쿼리스트링에서 온 id 는 문자열이라 그대로 filter 에 넣으면 ValueError 로 500 이 난다."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class ProblemSetAPI(APIView):
    @teacher_required
    def get(self, request):
        problem_set_id = request.GET.get("id")
        if problem_set_id:
            problem_set = owned_problem_set(request.user, problem_set_id)
            if not problem_set:
                return self.error("문제집이 존재하지 않습니다")
            problem_set = ProblemSet.objects.prefetch_related(
                "items__problem", "assignments__school_class__school").get(id=problem_set.id)
            return self.success(ProblemSetDetailSerializer(problem_set).data)

        problem_sets = ProblemSet.objects.annotate(
            problem_count=Count("items", distinct=True),
            assignment_count=Count("assignments", distinct=True))
        if not request.user.is_super_admin():
            problem_sets = problem_sets.filter(created_by=request.user)
        return self.success(ProblemSetSerializer(problem_sets, many=True).data)

    @validate_serializer(CreateProblemSetSerializer)
    @teacher_required
    def post(self, request):
        problem_set = ProblemSet.objects.create(title=request.data["title"],
                                                description=request.data["description"],
                                                created_by=request.user)
        return self.success(ProblemSetSerializer(problem_set).data)

    @validate_serializer(EditProblemSetSerializer)
    @teacher_required
    def put(self, request):
        problem_set = owned_problem_set(request.user, request.data["id"])
        if not problem_set:
            return self.error("문제집이 존재하지 않습니다")
        problem_set.title = request.data["title"]
        problem_set.description = request.data["description"]
        problem_set.save(update_fields=["title", "description", "last_update_time"])
        return self.success(ProblemSetSerializer(problem_set).data)

    @teacher_required
    def delete(self, request):
        """문제집만 지운다. 학생의 제출 기록은 문제에 달려 있어 영향을 받지 않는다."""
        problem_set = owned_problem_set(request.user, request.GET.get("id"))
        if not problem_set:
            return self.error("문제집이 존재하지 않습니다")
        problem_set.delete()
        return self.success()


class ProblemSetProblemAPI(APIView):
    @validate_serializer(ProblemSetProblemSerializer)
    @teacher_required
    def post(self, request):
        """문제를 문제집 끝에 추가한다. 이미 담긴 문제는 조용히 건너뛴다."""
        problem_set = owned_problem_set(request.user, request.data["problem_set"])
        if not problem_set:
            return self.error("문제집이 존재하지 않습니다")

        # 문제집에는 공개 문제만 담는다. 대회 문제를 담으면 대회 전에 내용이 새어나간다.
        problems = Problem.objects.filter(id__in=request.data["problems"],
                                          contest_id__isnull=True, visible=True)
        if not problems:
            return self.error("문제가 존재하지 않습니다")

        existing = set(problem_set.items.values_list("problem_id", flat=True))
        next_order = (problem_set.items.aggregate(m=Max("order"))["m"] or 0) + 1
        added = 0
        with transaction.atomic():
            for problem in problems:
                if problem.id in existing:
                    continue
                ProblemSetItem.objects.create(problem_set=problem_set, problem=problem,
                                              order=next_order)
                next_order += 1
                added += 1
        return self.success({"added": added})

    @validate_serializer(ProblemSetItemOrderSerializer)
    @teacher_required
    def put(self, request):
        """순서 변경. 받은 항목 id 순서대로 order 를 다시 매긴다."""
        problem_set = owned_problem_set(request.user, request.data["problem_set"])
        if not problem_set:
            return self.error("문제집이 존재하지 않습니다")

        items = {item.id: item for item in problem_set.items.all()}
        if set(request.data["items"]) != set(items.keys()):
            return self.error("문제 목록이 바뀌었습니다. 새로고침 후 다시 시도하세요")

        with transaction.atomic():
            for order, item_id in enumerate(request.data["items"], start=1):
                item = items[item_id]
                item.order = order
                item.save(update_fields=["order"])
        return self.success()

    @teacher_required
    def delete(self, request):
        item_id = int_or_none(request.GET.get("id"))
        if item_id is None:
            return self.error("잘못된 요청입니다. id가 필요합니다")
        item = ProblemSetItem.objects.filter(id=item_id).first()
        if not item or not owned_problem_set(request.user, item.problem_set_id):
            return self.error("문제가 존재하지 않습니다")
        item.delete()
        return self.success()


class ProblemSetAssignmentAPI(APIView):
    """문제집을 학급에 배포한다. 문제집과 학급 양쪽의 소유권을 모두 확인한다."""

    @validate_serializer(CreateProblemSetAssignmentSerializer)
    @teacher_required
    def post(self, request):
        # 마감일을 datetime 그대로 쓰기 위해 직렬화 결과 대신 validated_data 를 본다
        data = request.serializer.validated_data
        problem_set = owned_problem_set(request.user, data["problem_set"])
        if not problem_set:
            return self.error("문제집이 존재하지 않습니다")
        if not owned_class(request.user, data["school_class"]):
            return self.error("학급이 존재하지 않습니다")

        try:
            assignment = ProblemSetAssignment.objects.create(
                problem_set=problem_set, school_class_id=data["school_class"],
                due_at=data["due_at"], is_open=data["is_open"])
        except IntegrityError:
            return self.error("이미 이 학급에 배포한 문제집입니다")
        return self.success({"id": assignment.id})

    @validate_serializer(EditProblemSetAssignmentSerializer)
    @teacher_required
    def put(self, request):
        # request.data 는 직렬화 결과라 보내지 않은 due_at 도 None 으로 들어온다.
        # 공개 여부만 바꿀 때 마감일이 지워지지 않도록 validated_data 를 본다.
        data = request.serializer.validated_data
        assignment = self._owned_assignment(request.user, data["id"])
        if not assignment:
            return self.error("배포 기록이 존재하지 않습니다")
        for field in ("due_at", "is_open"):
            if field in data:
                setattr(assignment, field, data[field])
        assignment.save(update_fields=["due_at", "is_open"])
        return self.success()

    @teacher_required
    def delete(self, request):
        assignment = self._owned_assignment(request.user, request.GET.get("id"))
        if not assignment:
            return self.error("배포 기록이 존재하지 않습니다")
        assignment.delete()
        return self.success()

    @staticmethod
    def _owned_assignment(user, assignment_id):
        assignment_id = int_or_none(assignment_id)
        if assignment_id is None:
            return None
        assignment = ProblemSetAssignment.objects.filter(id=assignment_id).first()
        if not assignment or not owned_problem_set(user, assignment.problem_set_id):
            return None
        return assignment
