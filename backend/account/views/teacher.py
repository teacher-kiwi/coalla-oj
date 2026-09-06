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
from django.db.models import Max

from options.options import SysOptions
from submission.models import Submission
from submission.serializers import TeacherStudentSubmissionSerializer
from utils.api import APIView, validate_serializer
from utils.shortcuts import int_or_none, rand_str
from ..decorators import teacher_required
from ..login_throttle import clear_login_failures
from ..models import (AdminType, ClassMembership, School, SchoolClass, User,
                      UserProfile, generate_student_usernames)
from ..serializers import (ClassMembershipSerializer, CreateSchoolClassSerializer,
                           CreateStudentsSerializer, EditSchoolClassSerializer,
                           EditStudentNicknameSerializer,
                           ResetStudentPasswordSerializer, SchoolClassOrderSerializer,
                           SchoolClassSerializer, SchoolSerializer)

# 학생 비밀번호는 숫자 4자리로 고정한다(초등학생이 외울 수 있는 수준).
# 무차별 대입에 취약하므로 로그인 실패 잠금이 반드시 함께 동작해야 한다.
PIN_LENGTH = 4


def generate_pin():
    return "".join(random.choice("0123456789") for _ in range(PIN_LENGTH))


def owned_class(user, class_id):
    """내가 담당하는 학급만 돌려준다. 아니면 None.

    id 는 쿼리스트링에서 문자열로 온다. 숫자가 아니면 여기서 걸러야 한다.
    """
    class_id = int_or_none(class_id)
    if class_id is None:
        return None
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
        # 교사가 정한 차례로 준다. 이 응답이 대회·문제집의 배포 학급 표에도 그대로 쓰여,
        # 한 곳에서 순서를 바꾸면 모든 화면이 같이 따라온다.
        # 아직 순서를 손대지 않은 학급(order=0)은 뒤의 기준으로 갈린다.
        return self.success(SchoolClassSerializer(
            classes.order_by("order", "-year", "grade", "class_no"), many=True).data)

    @validate_serializer(CreateSchoolClassSerializer)
    @teacher_required
    def post(self, request):
        data = request.data
        try:
            school = School.objects.get(id=data["school"])
        except School.DoesNotExist:
            return self.error("학교가 존재하지 않습니다")

        # 새 학급은 맨 뒤에 붙인다. 0 으로 두면 이미 순서를 정해 둔 학급들 앞으로 끼어든다.
        next_order = (SchoolClass.objects.filter(teacher=request.user)
                      .aggregate(m=Max("order"))["m"] or 0) + 1
        try:
            school_class = SchoolClass.objects.create(
                school=school, teacher=request.user, year=data["year"],
                grade=data["grade"], class_no=data["class_no"], order=next_order)
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
        """학급과 소속 학생 계정을 함께 삭제한다.

        한 해가 끝나 학생의 기록을 남기지 않으려 할 때 쓴다. 잠시 막아두려는
        것이면 is_archived 로 끄면 된다(기록이 남고 다시 켤 수 있다).

        제출 기록, 즐겨찾기, 대회 순위가 CASCADE 로 함께 사라진다.
        문제의 정답률(submission_number/accepted_number)은 일부러 다시 세지 않는다.
        "지금까지 몇 명이 도전해 몇 번 맞혔나" 는 학생이 떠난 뒤에도 남아야 하는
        값이라서다. 다만 그 문제에 재채점이 일어나면 살아 있는 제출만으로 다시
        세므로 지워진 몫이 그때 사라진다(judge/recompute.py). 아직 못 맞춘 부분이다.
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
            # 다른 학급에도 속한 학생은 남긴다(현재 정책상 드물지만 안전하게).
            # 그래서 소속 수가 아니라 실제로 지운 계정 수를 돌려준다.
            orphans = User.objects.filter(id__in=student_ids, class_memberships__isnull=True)
            deleted_students = orphans.count()
            orphans.delete()
        return self.success({"deleted_students": deleted_students})


class SchoolClassOrderAPI(APIView):
    """학급 순서 변경. 받은 id 순서대로 order 를 다시 매긴다.

    문제집의 문제 순서(ProblemSetProblemAPI.put)와 같은 방식이다. 화면이 바꾼
    자리 하나가 아니라 목록 전체를 보내므로, 서버가 받은 차례를 그대로 확정한다.
    """
    @validate_serializer(SchoolClassOrderSerializer)
    @teacher_required
    def put(self, request):
        # 화면이 보여주는 것과 같은 범위(내 학급 전부)를 견준다.
        # 학급 목록은 비활성 학급도 함께 보여주고 거기서 순서를 바꾼다.
        classes = {c.id: c for c in SchoolClass.objects.filter(teacher=request.user)}
        if set(request.data["classes"]) != set(classes.keys()):
            return self.error("학급 목록이 바뀌었습니다. 새로고침 후 다시 시도하세요")

        for order, class_id in enumerate(request.data["classes"], start=1):
            classes[class_id].order = order
        SchoolClass.objects.bulk_update(classes.values(), ["order"])
        return self.success()


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
            taken_numbers = ", ".join(map(str, sorted(taken)))
            return self.error(f"이미 사용 중인 번호입니다: {taken_numbers}")

        limit = SysOptions.max_students_per_teacher
        current = ClassMembership.objects.filter(school_class__teacher=school_class.teacher).count()
        if current + len(numbers) > limit:
            return self.error(f"교사당 학생 수 상한({limit}명)을 넘습니다. 현재 {current}명")

        # 한 학급이 30명이면 한 명씩 만들 때 90번의 INSERT 가 나간다. 세 번으로 끝낸다.
        # (PostgreSQL 은 bulk_create 가 만든 객체에 pk 를 채워주므로 이어서 참조할 수 있다)
        created = [(number, generate_pin()) for number in numbers]
        usernames = generate_student_usernames(len(created))
        students = [User(username=username,
                         admin_type=AdminType.REGULAR_USER,
                         created_by=school_class.teacher,
                         password=make_password(pin))
                    for (number, pin), username in zip(created, usernames)]
        with transaction.atomic():
            User.objects.bulk_create(students)
            UserProfile.objects.bulk_create([UserProfile(user=student) for student in students])
            ClassMembership.objects.bulk_create(
                [ClassMembership(school_class=school_class, student=student, number=number,
                                 nickname=f"학생{number}")
                 for (number, _), student in zip(created, students)])

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
        membership = self._owned_membership(request.user, request.data["membership"])
        if membership is None:
            return self.error("학생이 존재하지 않습니다")

        pin = generate_pin()
        membership.student.set_password(pin)
        membership.student.save(update_fields=["password"])
        clear_login_failures(membership.school_class_id, membership.number)
        return self.success({"number": membership.number, "password": pin})

    @teacher_required
    def delete(self, request):
        membership_id = int_or_none(request.GET.get("id"))
        if membership_id is None:
            return self.error("잘못된 요청입니다. id가 필요합니다")
        membership = self._owned_membership(request.user, membership_id)
        if membership is None:
            return self.error("학생이 존재하지 않습니다")
        membership.student.delete()   # 소속과 제출 기록도 함께 삭제된다
        return self.success()

    @staticmethod
    def _owned_membership(teacher, membership_id):
        if membership_id is None:
            return None
        membership = ClassMembership.objects.select_related(
            "school_class", "student").filter(id=membership_id).first()
        if membership is None or not owned_class(teacher, membership.school_class_id):
            return None
        return membership


class StudentNicknameAPI(APIView):
    """학생 닉네임. 교사가 자기 학생을 알아보기 위한 이름이다.

    공개 화면에는 나가지 않는다(순위·채점 목록은 무작위 아이디로 표시된다).
    학급마다 붙이는 값이라 다른 학급과 겹쳐도 막지 않는다.
    """
    @validate_serializer(EditStudentNicknameSerializer)
    @teacher_required
    def put(self, request):
        membership = StudentAPI._owned_membership(request.user, request.data["membership"])
        if membership is None:
            return self.error("학생이 존재하지 않습니다")
        nickname = request.data["nickname"].strip()
        if not nickname:
            return self.error("닉네임을 입력해주세요")
        membership.nickname = nickname
        membership.save(update_fields=["nickname"])
        return self.success(ClassMembershipSerializer(membership).data)


class StudentSubmissionAPI(APIView):
    """담당 학생 한 명의 제출 이력.

    코드 열람은 기존 제출 상세 API(`/api/submission?id=`)로 한다.
    `Submission.check_user_permission` 이 담당 교사를 통과시킨다.
    """
    @teacher_required
    def get(self, request):
        membership_id = int_or_none(request.GET.get("membership"))
        if membership_id is None:
            return self.error("잘못된 요청입니다. membership이 필요합니다")
        membership = ClassMembership.objects.select_related("school_class").filter(
            id=membership_id).first()
        if not membership or not owned_class(request.user, membership.school_class_id):
            return self.error("학생이 존재하지 않습니다")

        submissions = Submission.objects.filter(user_id=membership.student_id,
                                                contest_id__isnull=True) \
                                        .select_related("problem")
        problem_id = int_or_none(request.GET.get("problem_id"))
        if problem_id is not None:
            submissions = submissions.filter(problem_id=problem_id)
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
