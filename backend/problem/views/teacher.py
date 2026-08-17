"""교사 전용 문제·문제집 API (/api/teacher/problem*).

교사는 `is_admin_role()` 에서 제외되어 있어 /api/admin/* 을 쓸 수 없다.
여기의 모든 조회·수정은 "내가 만든 문제집"과 "내가 담당하는 학급"으로 범위를 좁힌다.
"""
import io
from urllib.parse import quote

import xlsxwriter
from django.db import IntegrityError
from django.db.models import Count, Max, Q
from django.http import HttpResponse
from django.utils.timezone import now

from options.options import SysOptions
from account.decorators import teacher_required
from account.views.teacher import owned_class
from submission.models import JudgeStatus, Submission
from utils.api import APIView, validate_serializer
from utils.shortcuts import int_or_none

from ..models import (Problem, ProblemRuleType, ProblemSet, ProblemSetAssignment,
                      ProblemSetItem, ProblemVisibility)
from ..serializers import (CreateProblemSetAssignmentSerializer, CreateProblemSetSerializer,
                           EditProblemSetAssignmentSerializer, EditProblemSetSerializer,
                           EditTeacherProblemSerializer, ProblemAdminSerializer,
                           ProblemSetDetailSerializer, ProblemSetItemOrderSerializer,
                           ProblemSetProblemSerializer, ProblemSetSerializer,
                           TeacherProblemListSerializer, TeacherProblemSerializer)
from .admin import get_existing_problem_tags, TestCaseZipProcessor


def owned_problem_set(user, problem_set_id, queryset=None):
    """내가 만든 문제집만 돌려준다. 아니면 None.

    최고관리자는 운영·점검을 위해 통과시킨다(`owned_class` 와 같은 규칙).
    상세 화면처럼 딸린 항목까지 필요하면 prefetch 를 건 queryset 을 넘긴다.
    """
    problem_set_id = int_or_none(problem_set_id)
    if problem_set_id is None:
        return None
    qs = ProblemSet.objects.all() if queryset is None else queryset
    if user.is_super_admin():
        return qs.filter(id=problem_set_id).first()
    return qs.filter(id=problem_set_id, created_by=user).first()


class ProblemSetAPI(APIView):
    @teacher_required
    def get(self, request):
        problem_set_id = request.GET.get("id")
        if problem_set_id:
            problem_set = owned_problem_set(
                request.user, problem_set_id,
                queryset=ProblemSet.objects.prefetch_related(
                    "items__problem", "assignments__school_class__school"))
            if not problem_set:
                return self.error("문제집이 존재하지 않습니다")
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

        # 공개 문제와 "내가 만든 문제"만 담을 수 있다.
        # 대회 문제는 대회 전에 내용이 새어나가므로 제외한다.
        problems = Problem.objects.filter(
            Q(visibility=ProblemVisibility.public) | Q(created_by=request.user),
            id__in=request.data["problems"], contest_id__isnull=True, visible=True)
        if not problems:
            return self.error("문제가 존재하지 않습니다")

        existing = set(problem_set.items.values_list("problem_id", flat=True))
        next_order = (problem_set.items.aggregate(m=Max("order"))["m"] or 0) + 1
        new_items = []
        for problem in problems:
            if problem.id in existing:
                continue
            new_items.append(ProblemSetItem(problem_set=problem_set, problem=problem,
                                            order=next_order))
            next_order += 1
        ProblemSetItem.objects.bulk_create(new_items)
        return self.success({"added": len(new_items)})

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

        for order, item_id in enumerate(request.data["items"], start=1):
            items[item_id].order = order
        ProblemSetItem.objects.bulk_update(items.values(), ["order"])
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


class ProblemSetProgressAPI(APIView):
    """학급 × 문제집 진도표.

    셀 하나는 "학생이 그 문제를 풀었는지 / 몇 번 시도했는지"다. 진도는
    UserProfile 의 상태값 대신 제출 테이블을 직접 집계한다. 시도 횟수는
    프로필에 없고, "풀지는 못했지만 붙들고 있는 문제"가 교사에게 가장 필요한 정보다.
    """
    @teacher_required
    def get(self, request):
        problem_set = owned_problem_set(request.user, request.GET.get("problem_set"))
        if not problem_set:
            return self.error("문제집이 존재하지 않습니다")
        school_class = owned_class(request.user, request.GET.get("class_id"))
        if not school_class:
            return self.error("학급이 존재하지 않습니다")

        problems = [item.problem for item in problem_set.items.select_related("problem")]
        memberships = list(school_class.memberships.select_related("student"))
        cells = self._submission_cells([m.student_id for m in memberships],
                                       [p.id for p in problems])

        students = []
        for membership in memberships:
            row = [cells.get((membership.student_id, p.id), _EMPTY_CELL) for p in problems]
            students.append({
                "membership": membership.id,
                "number": membership.number,
                "solved_count": sum(1 for cell in row if cell["solved"]),
                "cells": row,
            })

        totals = [{
            "solved": sum(1 for s in students if s["cells"][index]["solved"]),
            "tried": sum(1 for s in students if s["cells"][index]["attempts"]),
        } for index in range(len(problems))]

        data = {
            "problem_set": {"id": problem_set.id, "title": problem_set.title},
            "school_class": {"id": school_class.id, "name": str(school_class)},
            "problems": [{"id": p.id, "_id": p._id, "title": p.title} for p in problems],
            "students": students,
            "totals": totals,
        }
        if request.GET.get("download") == "1":
            return _progress_xlsx(data)
        return self.success(data)

    @staticmethod
    def _submission_cells(student_ids, problem_ids):
        """(학생, 문제) -> {시도 횟수, 정답 여부}. 한 번의 집계 쿼리로 끝낸다."""
        if not student_ids or not problem_ids:
            return {}
        rows = (Submission.objects
                .filter(contest_id__isnull=True, user_id__in=student_ids,
                        problem_id__in=problem_ids)
                .values("user_id", "problem_id")
                .annotate(attempts=Count("id"),
                          accepted=Count("id", filter=Q(result=JudgeStatus.ACCEPTED))))
        return {(row["user_id"], row["problem_id"]):
                {"attempts": row["attempts"], "solved": row["accepted"] > 0}
                for row in rows}


_EMPTY_CELL = {"attempts": 0, "solved": False}


def _progress_xlsx(data):
    """진도표 내려받기.

    csv 는 한글 인코딩 때문에 엑셀에서 깨지기 쉬워 xlsx 로 준다.
    학생 계정 배부용 파일과 달리 개인정보(PIN)가 없어 메모리에서 바로 흘려보낸다.
    """
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    worksheet = workbook.add_worksheet()
    worksheet.set_column("A:A", 8)
    worksheet.write(0, 0, "번호")
    for index, problem in enumerate(data["problems"]):
        worksheet.write(0, 1 + index, "{} {}".format(problem["_id"], problem["title"]))
    worksheet.write(0, 1 + len(data["problems"]), "해결")

    for row, student in enumerate(data["students"], start=1):
        worksheet.write_number(row, 0, student["number"])
        for index, cell in enumerate(student["cells"]):
            if cell["solved"]:
                worksheet.write_string(row, 1 + index, "O")
            elif cell["attempts"]:
                worksheet.write_string(row, 1 + index, "△({})".format(cell["attempts"]))
            else:
                worksheet.write_string(row, 1 + index, "")
        worksheet.write_string(row, 1 + len(data["problems"]),
                               "{}/{}".format(student["solved_count"], len(data["problems"])))
    workbook.close()

    response = HttpResponse(output.getvalue())
    filename = quote("{} {}.xlsx".format(data["school_class"]["name"], data["problem_set"]["title"]))
    response["Content-Disposition"] = f"attachment; filename*=UTF-8''{filename}"
    response["Content-Type"] = "application/xlsx"
    return response


class TeacherProblemAPI(APIView, TestCaseZipProcessor):
    """교사가 직접 만드는 문제.

    관리자 출제 화면과 달리 표시 번호·시간 제한·특수 채점·코드 템플릿을 받지 않는다.
    새 문제는 비공개로 만들어지고, 공개는 따로 신청해 관리자 승인을 받는다.
    """
    # 시간·메모리는 초등 수준의 문제에 넉넉한 값으로 고정한다
    DEFAULT_TIME_LIMIT = 2000
    DEFAULT_MEMORY_LIMIT = 256

    @teacher_required
    def get(self, request):
        problem_id = int_or_none(request.GET.get("id"))
        if problem_id is not None:
            problem = self._owned(request.user, problem_id)
            if not problem:
                return self.error("문제가 존재하지 않습니다")
            return self.success(ProblemAdminSerializer(problem).data)

        problems = (Problem.objects.filter(created_by=request.user, contest_id__isnull=True)
                    .prefetch_related("tags"))
        return self.success(TeacherProblemListSerializer(problems, many=True).data)

    @validate_serializer(TeacherProblemSerializer)
    @teacher_required
    def post(self, request):
        data = request.data
        tag_objs, error = get_existing_problem_tags(data["tags"])
        if error:
            return self.error(error)

        cases = request.serializer.validated_data["cases"]
        info, test_case_id = self.process_cases(cases)
        problem = Problem.objects.create(
            _id=Problem.next_display_id(),
            title=data["title"],
            description=data["description"],
            input_description=data["input_description"],
            output_description=data["output_description"],
            hint=data.get("hint") or "",
            samples=[{"input": c["input"], "output": c["output"]}
                     for c in cases if c["is_sample"]],
            test_case_id=test_case_id,
            test_case_score=[{"input_name": c["input_name"], "output_name": c["output_name"],
                              "score": 100 // len(info)} for c in info],
            languages=SysOptions.language_names,
            template={},
            time_limit=self.DEFAULT_TIME_LIMIT,
            memory_limit=self.DEFAULT_MEMORY_LIMIT,
            difficulty=data["difficulty"],
            visibility=ProblemVisibility.private,
            rule_type=ProblemRuleType.ACM,
            created_by=request.user,
            source="")
        problem.tags.set(tag_objs)
        return self.success(TeacherProblemListSerializer(problem).data)

    @validate_serializer(EditTeacherProblemSerializer)
    @teacher_required
    def put(self, request):
        data = request.data
        problem = self._owned(request.user, data["id"])
        if not problem:
            return self.error("문제가 존재하지 않습니다")
        if problem.visibility == ProblemVisibility.public:
            return self.error("공개된 문제는 관리자만 수정할 수 있습니다")

        tag_objs, error = get_existing_problem_tags(data["tags"])
        if error:
            return self.error(error)

        cases = request.serializer.validated_data.get("cases")
        if cases:
            # 테스트케이스를 다시 만들면 예제와 배점도 함께 갱신한다
            info, test_case_id = self.process_cases(cases)
            problem.test_case_id = test_case_id
            problem.test_case_score = [{"input_name": c["input_name"],
                                        "output_name": c["output_name"],
                                        "score": 100 // len(info)} for c in info]
            problem.samples = [{"input": c["input"], "output": c["output"]}
                               for c in cases if c["is_sample"]]

        problem.title = data["title"]
        problem.description = data["description"]
        problem.input_description = data["input_description"]
        problem.output_description = data["output_description"]
        problem.hint = data.get("hint") or ""
        problem.difficulty = data["difficulty"]
        problem.last_update_time = now()
        problem.save()
        problem.tags.set(tag_objs)
        return self.success(TeacherProblemListSerializer(problem).data)

    @teacher_required
    def delete(self, request):
        problem = self._owned(request.user, int_or_none(request.GET.get("id")))
        if not problem:
            return self.error("문제가 존재하지 않습니다")
        if problem.visibility == ProblemVisibility.public:
            return self.error("공개된 문제는 삭제할 수 없습니다. 관리자에게 문의하세요")
        if Submission.objects.filter(problem=problem).exists():
            return self.error("이미 제출 기록이 있어 삭제할 수 없습니다")
        problem.delete()
        return self.success()

    @staticmethod
    def _owned(user, problem_id):
        if problem_id is None:
            return None
        return Problem.objects.filter(id=problem_id, created_by=user,
                                      contest_id__isnull=True).first()


class TeacherProblemPublishAPI(APIView):
    """공개 신청. 비공개 → 승인 대기로 바꾼다. 승인은 관리자가 한다."""
    @teacher_required
    def post(self, request):
        problem = TeacherProblemAPI._owned(request.user, int_or_none(request.data.get("id")))
        if not problem:
            return self.error("문제가 존재하지 않습니다")
        if problem.visibility != ProblemVisibility.private:
            return self.error("이미 공개를 신청했거나 공개된 문제입니다")
        problem.visibility = ProblemVisibility.pending
        problem.save(update_fields=["visibility"])
        return self.success()

    @teacher_required
    def delete(self, request):
        """신청 취소. 승인 전에만 된다."""
        problem = TeacherProblemAPI._owned(request.user, int_or_none(request.GET.get("id")))
        if not problem:
            return self.error("문제가 존재하지 않습니다")
        if problem.visibility != ProblemVisibility.pending:
            return self.error("공개 신청 중인 문제가 아닙니다")
        problem.visibility = ProblemVisibility.private
        problem.save(update_fields=["visibility"])
        return self.success()
