"""수업용 학생 계정의 로그인과 비밀번호 변경.

학생은 아이디를 외우지 않는다. 학교 → 학년·반 → 담당 교사를 검색으로 고르고
자기 번호와 PIN 4자리만 입력한다.

인증 자체는 기존 경로를 그대로 재사용한다. 새로 만든 것은 "사용자를 어떻게 찾는가"뿐이다.
관리자 로그인(/api/login)은 건드리지 않는다 — 구글 장애 시 유일한 비상 접속 경로다.
"""
from django.contrib import auth

from utils.api import APIView, validate_serializer
from ..decorators import login_required
from ..login_throttle import clear_login_failures, lock_remaining, record_failure
from ..models import ClassMembership, School, SchoolClass
from ..serializers import (SchoolSerializer, StudentChangePasswordSerializer,
                           StudentLoginSerializer)


class StudentSchoolSearchAPI(APIView):
    """로그인 전에 호출된다. 학급이 등록된 학교만 노출한다."""
    def get(self, request):
        keyword = request.GET.get("keyword", "").strip()
        if len(keyword) < 2:
            return self.error("학교 이름을 두 글자 이상 입력해주세요")
        schools = School.objects.filter(name__icontains=keyword,
                                        classes__is_archived=False).distinct()[:20]
        return self.success(SchoolSerializer(schools, many=True).data)


class StudentClassSearchAPI(APIView):
    """선택한 학교의 학급 목록. 교사 닉네임까지 보여주고 학생이 자기 반을 고른다."""
    def get(self, request):
        school_id = request.GET.get("school_id")
        if not school_id:
            return self.error("학교를 선택해주세요")
        classes = SchoolClass.objects.filter(school_id=school_id, is_archived=False) \
            .select_related("teacher")
        grade = request.GET.get("grade")
        if grade:
            classes = classes.filter(grade=grade)
        return self.success([{
            "id": c.id,
            "grade": c.grade,
            "class_no": c.class_no,
            "teacher_name": c.teacher.username,
        } for c in classes])


class StudentLoginAPI(APIView):
    @validate_serializer(StudentLoginSerializer)
    def post(self, request):
        data = request.data
        class_id, number = data["school_class"], data["number"]

        remaining = lock_remaining(class_id, number)
        if remaining:
            minutes = max(1, remaining // 60)
            return self.error(f"로그인 시도가 많아 잠겼습니다. {minutes}분 후 다시 시도하거나 "
                              f"선생님께 초기화를 요청하세요")

        membership = ClassMembership.objects.select_related("student", "school_class") \
            .filter(school_class_id=class_id, number=number).first()

        user = None
        if membership is not None:
            # 인증은 기존 경로를 그대로 쓴다
            user = auth.authenticate(username=membership.student.username,
                                     password=data["password"])

        if user is None:
            # 번호가 없는 경우와 비밀번호가 틀린 경우를 구분해서 알려주지 않는다
            locked = record_failure(class_id, number)
            if locked:
                minutes = max(1, locked // 60)
                return self.error(f"로그인 시도가 많아 {minutes}분간 잠겼습니다. "
                                  f"선생님께 초기화를 요청하세요")
            return self.error("번호 또는 비밀번호가 올바르지 않습니다")

        if user.is_disabled:
            return self.error("사용할 수 없는 계정입니다. 선생님께 문의하세요")

        clear_login_failures(class_id, number)
        auth.login(request, user)
        return self.success("Succeeded")


class StudentChangePasswordAPI(APIView):
    """학생이 자기 PIN 을 바꾼다. 일반 비밀번호 변경 API 는 6자 이상을 요구해 쓸 수 없다."""
    @validate_serializer(StudentChangePasswordSerializer)
    @login_required
    def post(self, request):
        user = request.user
        if user.created_by_id is None:
            return self.error("학교에서 발급받은 계정만 사용할 수 있습니다")

        data = request.data
        if auth.authenticate(username=user.username, password=data["old_password"]) is None:
            return self.error("기존 비밀번호가 올바르지 않습니다")
        if data["new_password"] == data["old_password"]:
            return self.error("기존 비밀번호와 다른 번호를 입력해주세요")

        user.set_password(data["new_password"])
        user.save(update_fields=["password"])
        return self.success("Succeeded")
