"""교사 전용 API (/api/teacher/*).

교사는 `is_admin_role()` 에서 의도적으로 제외되어 있어 /api/admin/* 을 쓸 수 없다.
여기의 모든 조회·수정은 "내가 만든 학급"으로 범위를 좁힌다.
"""
import os
import random
import re

import xlsxwriter
from django.http import HttpResponse
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError, transaction

from options.options import SysOptions
from submission.models import Submission
from submission.serializers import TeacherStudentSubmissionSerializer
from utils.api import APIView, validate_serializer
from utils.shortcuts import rand_str
from ..decorators import teacher_required
from ..login_throttle import clear_login_failures
from ..models import (AdminType, ClassMembership, School, SchoolClass, User,
                      UserProfile)
from ..serializers import (ClassMembershipSerializer, CreateSchoolClassSerializer,
                           CreateStudentsSerializer, EditSchoolClassSerializer,
                           ResetStudentPasswordSerializer, SchoolClassSerializer,
                           SchoolSerializer)

# 학생 비밀번호는 숫자 4자리로 고정한다(초등학생이 외울 수 있는 수준).
# 무차별 대입에 취약하므로 로그인 실패 잠금이 반드시 함께 동작해야 한다.
PIN_LENGTH = 4


def generate_pin():
    return "".join(random.choice("0123456789") for _ in range(PIN_LENGTH))


def owned_class(user, class_id):
    """내가 담당하는 학급만 돌려준다. 아니면 None."""
    qs = SchoolClass.objects.select_related("school", "teacher")
    if user.is_super_admin():
        return qs.filter(id=class_id).first()
    return qs.filter(id=class_id, teacher=user).first()


class SchoolListAPI(APIView):
    """학급을 만들 때 학교를 고르기 위한 검색. 교사만 사용한다."""
    @teacher_required
    def get(self, request):
        keyword = request.GET.get("keyword", "").strip()
        schools = School.objects.all()
        if keyword:
            schools = schools.filter(name__icontains=keyword)
        return self.success(self.paginate_data(request, schools, SchoolSerializer))


class SchoolClassAPI(APIView):
    @teacher_required
    def get(self, request):
        class_id = request.GET.get("id")
        if class_id:
            school_class = owned_class(request.user, class_id)
            if not school_class:
                return self.error("학급이 존재하지 않습니다")
            return self.success(SchoolClassSerializer(school_class).data)

        classes = SchoolClass.objects.select_related("school", "teacher")
        if not request.user.is_super_admin():
            classes = classes.filter(teacher=request.user)
        if request.GET.get("archived") != "true":
            classes = classes.filter(is_archived=False)
        return self.success(SchoolClassSerializer(classes, many=True).data)

    @validate_serializer(CreateSchoolClassSerializer)
    @teacher_required
    def post(self, request):
        data = request.data
        try:
            school = School.objects.get(id=data["school"])
        except School.DoesNotExist:
            return self.error("학교가 존재하지 않습니다")

        try:
            school_class = SchoolClass.objects.create(
                school=school, teacher=request.user, year=data["year"],
                grade=data["grade"], class_no=data["class_no"])
        except IntegrityError:
            return self.error("같은 학급이 이미 등록되어 있습니다")
        return self.success(SchoolClassSerializer(school_class).data)

    @validate_serializer(EditSchoolClassSerializer)
    @teacher_required
    def put(self, request):
        data = request.data
        school_class = owned_class(request.user, data["id"])
        if not school_class:
            return self.error("학급이 존재하지 않습니다")
        for field in ("year", "grade", "class_no", "is_archived"):
            if field in data:
                setattr(school_class, field, data[field])
        try:
            school_class.save()
        except IntegrityError:
            return self.error("같은 학급이 이미 등록되어 있습니다")
        return self.success(SchoolClassSerializer(school_class).data)

    @teacher_required
    def delete(self, request):
        """학급과 소속 학생 계정을 함께 삭제한다(학년 종료 처리).

        제출 기록도 CASCADE 로 사라진다. 문제 통계는 누적값이므로 재계산하지 않는다.
        """
        class_id = request.GET.get("id")
        if not class_id:
            return self.error("잘못된 요청입니다. id가 필요합니다")
        school_class = owned_class(request.user, class_id)
        if not school_class:
            return self.error("학급이 존재하지 않습니다")

        with transaction.atomic():
            student_ids = list(school_class.memberships.values_list("student_id", flat=True))
            school_class.delete()
            # 다른 학급에도 속한 학생은 남긴다(현재 정책상 드물지만 안전하게)
            User.objects.filter(id__in=student_ids, class_memberships__isnull=True).delete()
        return self.success({"deleted_students": len(student_ids)})


class StudentSheetAPI(APIView):
    """생성 직후 받은 file_id 로 계정 배부용 엑셀을 내려받는다."""
    @teacher_required
    def get(self, request):
        file_id = request.GET.get("file_id")
        if not file_id or not re.match(r"^[a-zA-Z0-9]+$", file_id):
            return self.error("잘못된 요청입니다")
        path = f"/tmp/{file_id}.xlsx"
        if not os.path.isfile(path):
            return self.error("파일이 존재하지 않습니다")
        with open(path, "rb") as f:
            data = f.read()
        os.remove(path)
        response = HttpResponse(data)
        response["Content-Disposition"] = "attachment; filename=students.xlsx"
        response["Content-Type"] = "application/xlsx"
        return response


class StudentAPI(APIView):
    @teacher_required
    def get(self, request):
        """학급의 학생 목록"""
        school_class = owned_class(request.user, request.GET.get("class_id"))
        if not school_class:
            return self.error("학급이 존재하지 않습니다")
        memberships = school_class.memberships.select_related("student")
        return self.success(ClassMembershipSerializer(memberships, many=True).data)

    @validate_serializer(CreateStudentsSerializer)
    @teacher_required
    def post(self, request):
        """번호 범위로 학생 계정을 한 번에 만들고 배부용 xlsx 를 준비한다."""
        data = request.data
        school_class = owned_class(request.user, data["school_class"])
        if not school_class:
            return self.error("학급이 존재하지 않습니다")
        if data["number_from"] > data["number_to"]:
            return self.error("시작 번호는 끝 번호보다 작아야 합니다")

        numbers = list(range(data["number_from"], data["number_to"] + 1))
        taken = set(school_class.memberships.filter(number__in=numbers)
                    .values_list("number", flat=True))
        if taken:
            return self.error(f"이미 사용 중인 번호입니다: {', '.join(map(str, sorted(taken)))}")

        limit = SysOptions.max_students_per_teacher
        current = ClassMembership.objects.filter(school_class__teacher=school_class.teacher).count()
        if current + len(numbers) > limit:
            return self.error(f"교사당 학생 수 상한({limit}명)을 넘습니다. 현재 {current}명")

        created = []
        with transaction.atomic():
            for number in numbers:
                pin = generate_pin()
                student = User.objects.create(
                    username=school_class.student_username(number),
                    admin_type=AdminType.REGULAR_USER,
                    created_by=school_class.teacher,
                    password=make_password(pin))
                UserProfile.objects.create(user=student)
                ClassMembership.objects.create(school_class=school_class,
                                               student=student, number=number)
                created.append((number, pin))

        # 초기 PIN 은 해시로 저장되어 다시 조회할 수 없다. 교사가 배부해야 하므로
        # 생성 직후 이 응답에서만 평문으로 돌려준다.
        return self.success({
            "file_id": _write_student_xlsx(school_class, created),
            "students": [{"number": n, "password": p} for n, p in created],
        })

    @validate_serializer(ResetStudentPasswordSerializer)
    @teacher_required
    def put(self, request):
        """학생 비밀번호 초기화. 새 PIN 을 돌려주므로 교사가 학생에게 알려준다."""
        try:
            membership = ClassMembership.objects.select_related(
                "school_class", "student").get(id=request.data["membership"])
        except ClassMembership.DoesNotExist:
            return self.error("학생이 존재하지 않습니다")
        if not owned_class(request.user, membership.school_class_id):
            return self.error("학생이 존재하지 않습니다")

        pin = generate_pin()
        membership.student.set_password(pin)
        membership.student.save(update_fields=["password"])
        clear_login_failures(membership.school_class_id, membership.number)
        return self.success({"number": membership.number, "password": pin})

    @teacher_required
    def delete(self, request):
        membership_id = request.GET.get("id")
        if not membership_id:
            return self.error("잘못된 요청입니다. id가 필요합니다")
        try:
            membership = ClassMembership.objects.select_related("school_class").get(id=membership_id)
        except ClassMembership.DoesNotExist:
            return self.error("학생이 존재하지 않습니다")
        if not owned_class(request.user, membership.school_class_id):
            return self.error("학생이 존재하지 않습니다")
        membership.student.delete()   # 소속과 제출 기록도 함께 삭제된다
        return self.success()


class StudentSubmissionAPI(APIView):
    """담당 학생 한 명의 제출 이력.

    코드 열람은 기존 제출 상세 API(`/api/submission?id=`)로 한다.
    `Submission.check_user_permission` 이 담당 교사를 통과시킨다.
    """
    @teacher_required
    def get(self, request):
        membership_id = request.GET.get("membership")
        if not membership_id or not membership_id.isdigit():
            return self.error("잘못된 요청입니다. membership이 필요합니다")
        membership = ClassMembership.objects.select_related("school_class").filter(
            id=int(membership_id)).first()
        if not membership or not owned_class(request.user, membership.school_class_id):
            return self.error("학생이 존재하지 않습니다")

        submissions = Submission.objects.filter(user_id=membership.student_id,
                                                contest_id__isnull=True) \
                                        .select_related("problem")
        problem_id = request.GET.get("problem_id")
        if problem_id and problem_id.isdigit():
            submissions = submissions.filter(problem_id=int(problem_id))
        return self.success(self.paginate_data(request, submissions,
                                               TeacherStudentSubmissionSerializer))


def _write_student_xlsx(school_class, created):
    """계정 배부용 엑셀. 다운로드는 기존 GenerateUserAPI 와 같은 방식으로 file_id 로 받는다."""
    file_id = rand_str(8)
    workbook = xlsxwriter.Workbook(f"/tmp/{file_id}.xlsx")
    worksheet = workbook.add_worksheet()
    worksheet.set_column("A:C", 22)
    worksheet.write("A1", "학교")
    worksheet.write("B1", "학급")
    worksheet.write("C1", "번호")
    worksheet.write("D1", "비밀번호")
    for row, (number, pin) in enumerate(created, start=1):
        worksheet.write_string(row, 0, school_class.school.name)
        worksheet.write_string(row, 1, school_class.display_name)
        worksheet.write_number(row, 2, number)
        worksheet.write_string(row, 3, pin)
    workbook.close()
    return file_id
