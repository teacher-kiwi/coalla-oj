import os
import re
import xlsxwriter

from django.db import transaction, IntegrityError
from django.db.models import Count, Q
from django.http import HttpResponse
from django.contrib.auth.hashers import make_password

from utils.api import APIView, validate_serializer
from utils.shortcuts import int_or_none, rand_str
from ..teaching import (delete_school_class, has_teaching_data, purge_teaching_data, teacher_accounts,
                        teaching_data_summary, transfer_conflicts, transfer_teaching_data)

from ..decorators import super_admin_required
from ..models import (AdminType, ProblemPermission, RESERVED_USERNAME_PREFIX_MESSAGE, SchoolClass, User, UserProfile,
                      is_reserved_username)
from ..serializers import EditUserSerializer, UserAdminSerializer, GenerateUserSerializer
from ..serializers import ImportUserSeralizer
from ..serializers import (AdminClassStudentSerializer, AdminSchoolClassSerializer, EditSchoolClassSerializer,
                           TransferTeachingDataSerializer)


class UserAdminAPI(APIView):
    @validate_serializer(ImportUserSeralizer)
    @super_admin_required
    def post(self, request):
        data = request.data["users"]

        user_list = []
        for user_data in data:
            if len(user_data) != 3 or not user_data[0].strip() or len(user_data[0]) > 32 or not user_data[1]:
                return self.error(f"데이터 처리 중 오류가 발생했습니다: '{user_data}'")
            user_list.append(User(username=user_data[0].strip(), password=make_password(user_data[1]),
                                  email=user_data[2].strip().lower() or None))

        try:
            with transaction.atomic():
                ret = User.objects.bulk_create(user_list)
                UserProfile.objects.bulk_create([UserProfile(user=u) for u in ret])
            return self.success()
        except IntegrityError:
            # 원본은 DB 예외 메시지(DETAIL: Key (username)=(root11) already exists.)를
            # 그대로 돌려줬다. 읽히지도 않고 DB 내부 구조만 드러난다.
            return self.error("이미 사용 중인 사용자명이 있습니다")

    @validate_serializer(EditUserSerializer)
    @super_admin_required
    def put(self, request):
        data = request.data
        try:
            user = User.objects.get(id=data["id"])
        except User.DoesNotExist:
            return self.error("사용자가 존재하지 않습니다")
        username = data["username"].strip().lower()
        email = (data["email"] or "").strip().lower() or None
        if not username:
            return self.error("사용자명을 적어주세요")
        if username != user.username and is_reserved_username(username):
            return self.error(RESERVED_USERNAME_PREFIX_MESSAGE)
        if User.objects.filter(username=username).exclude(id=user.id).exists():
            return self.error("이미 사용 중인 사용자명입니다")
        if email and User.objects.filter(email=email).exclude(id=user.id).exists():
            return self.error("이미 사용 중인 이메일입니다")
        # 자기 자신을 내리거나 막으면 관리자 페이지에 다시 들어올 수 없다
        if user.id == request.user.id and (data["admin_type"] != user.admin_type or data["is_disabled"]):
            return self.error("자기 계정의 유형을 바꾸거나 비활성화할 수 없습니다")
        # 권한은 관리자(Admin)에게만 준다. 최고관리자는 대회·캐릭터를 늘 갖고 수업은 하지 않으며,
        # 교사·일반 사용자에게는 의미가 없다.
        is_admin = data["admin_type"] == AdminType.ADMIN
        teacher_permission = is_admin and data["teacher_permission"]
        # 교사 기능을 잃으면 학급과 학생을 아무도 관리할 수 없게 된다.
        # 조용히 무력화하지 말고, 정리 기능으로 먼저 비우게 한다.
        stays_teacher = data["admin_type"] == AdminType.TEACHER or teacher_permission
        if user.is_teacher() and not stays_teacher and has_teaching_data(user):
            return self.error("담당 학급이나 문제가 남아 있어 교사 기능을 회수할 수 없습니다. "
                              "교육 데이터 정리(넘기기·지우기)를 먼저 진행하세요")

        user.username = username
        user.email = email
        user.admin_type = data["admin_type"]
        user.is_disabled = data["is_disabled"]
        user.teacher_permission = teacher_permission
        user.contest_permission = is_admin and data["contest_permission"]
        user.avatar_permission = is_admin and data["avatar_permission"]

        if data["admin_type"] == AdminType.ADMIN:
            user.problem_permission = data["problem_permission"]
        elif data["admin_type"] == AdminType.SUPER_ADMIN:
            user.problem_permission = ProblemPermission.ALL
        elif data["admin_type"] == AdminType.TEACHER:
            # 교사 승인(TeacherApplicationAdminAPI)과 같은 값을 준다
            user.problem_permission = ProblemPermission.OWN
        else:
            user.problem_permission = ProblemPermission.NONE

        if data["password"]:
            user.set_password(data["password"])

        user.save()
        return self.success(UserAdminSerializer(user).data)

    @super_admin_required
    def get(self, request):
        user_id = request.GET.get("id")
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return self.error("사용자가 존재하지 않습니다")
            return self.success(UserAdminSerializer(user).data)

        # 바로 과제 임시 계정은 과제마다 수십 개씩 생겼다 사라진다. 관리할 대상이 아니다.
        user = User.objects.exclude(admin_type=AdminType.GUEST).order_by("-create_time")

        keyword = request.GET.get("keyword", None)
        if keyword:
            user = user.filter(Q(username__icontains=keyword) |
                               Q(email__icontains=keyword))
        return self.success(self.paginate_data(request, user, UserAdminSerializer))

    @super_admin_required
    def delete(self, request):
        id = request.GET.get("id")
        if not id:
            return self.error("잘못된 요청입니다. id가 필요합니다")
        ids = id.split(",")
        if str(request.user.id) in ids:
            return self.error("현재 로그인한 사용자는 삭제할 수 없습니다")
        # 교사(교사 권한 받은 관리자 포함)를 그냥 지우면 학급과 학생이 주인 없이 남는다.
        # 삭제 전에 정리하게 한다. 권한을 회수한 뒤에도 데이터가 남을 수 있어 유형으로 거르지 않는다.
        blocked = [u.username for u in User.objects.filter(id__in=ids).exclude(admin_type=AdminType.GUEST)
                   if has_teaching_data(u)]
        if blocked:
            names = ", ".join(blocked)
            return self.error(f"교육 데이터가 남아 있는 교사가 있습니다: {names}. "
                              f"교육 데이터 정리(넘기기·지우기)를 먼저 진행하세요")
        User.objects.filter(id__in=ids).delete()
        return self.success()


class TeacherDataAPI(APIView):
    """교사에게 딸린 교육용 데이터 정리: 다른 교사에게 넘기기(기본) 또는 지우기.

    교사 기능을 회수하거나 계정을 지우기 전에 쓴다. 계정 자체는 남기므로,
    정리한 뒤에 유형을 바꾸거나 계정을 지울 수 있다.
    지우기는 되돌릴 수 없어서 GET 으로 먼저 무엇이 있는지 보여준다.
    """
    @super_admin_required
    def get(self, request):
        user = self._teacher(request.GET.get("id"))
        if user is None:
            return self.error("사용자가 존재하지 않습니다")
        # 넘겨받을 수 있는 교사. 비활성 계정에 넘기면 아무도 관리하지 못한다.
        targets = teacher_accounts().exclude(id=user.id).filter(is_disabled=False).order_by("username")
        return self.success({"username": user.username, **teaching_data_summary(user),
                             "teachers": [{"id": t.id, "username": t.username} for t in targets]})

    @validate_serializer(TransferTeachingDataSerializer)
    @super_admin_required
    def post(self, request):
        """다른 교사에게 넘긴다. 학생 계정과 기록은 그대로 남는다."""
        user = self._teacher(request.data["id"])
        target = self._teacher(request.data["to"])
        if user is None or target is None:
            return self.error("사용자가 존재하지 않습니다")
        if user.id == target.id:
            return self.error("같은 사람에게 넘길 수 없습니다")
        if not target.is_teacher() or target.is_disabled:
            return self.error("넘겨받는 사람이 교사가 아닙니다")
        conflicts = transfer_conflicts(user, target)
        if conflicts:
            names = ", ".join(conflicts)
            return self.error(f"{target.username} 선생님에게 같은 학급이 이미 있습니다: {names}. "
                              f"한쪽 학급을 먼저 정리하세요")
        return self.success(transfer_teaching_data(user, target))

    @super_admin_required
    def delete(self, request):
        user = self._teacher(request.GET.get("id"))
        if user is None:
            return self.error("사용자가 존재하지 않습니다")
        return self.success(purge_teaching_data(user))

    @staticmethod
    def _teacher(user_id):
        if not user_id:
            return None
        return User.objects.filter(id=int_or_none(user_id)).first()


class GenerateUserAPI(APIView):
    @super_admin_required
    def get(self, request):
        file_id = request.GET.get("file_id")
        if not file_id:
            return self.error("잘못된 요청입니다. file_id가 필요합니다")
        if not re.match(r"^[a-zA-Z0-9]+$", file_id):
            return self.error("file_id가 올바르지 않습니다")
        file_path = f"/tmp/{file_id}.xlsx"
        if not os.path.isfile(file_path):
            return self.error("파일이 존재하지 않습니다")
        with open(file_path, "rb") as f:
            raw_data = f.read()
        os.remove(file_path)
        response = HttpResponse(raw_data)
        response["Content-Disposition"] = "attachment; filename=users.xlsx"
        response["Content-Type"] = "application/xlsx"
        return response

    @validate_serializer(GenerateUserSerializer)
    @super_admin_required
    def post(self, request):
        data = request.data
        number_max_length = max(len(str(data["number_from"])), len(str(data["number_to"])))
        if number_max_length + len(data["prefix"]) + len(data["suffix"]) > 32:
            return self.error("사용자명은 32자를 넘을 수 없습니다")
        if data["number_from"] > data["number_to"]:
            return self.error("시작 번호는 끝 번호보다 작아야 합니다")

        file_id = rand_str(8)
        filename = f"/tmp/{file_id}.xlsx"
        workbook = xlsxwriter.Workbook(filename)
        worksheet = workbook.add_worksheet()
        worksheet.set_column("A:B", 20)
        worksheet.write("A1", "Username")
        worksheet.write("B1", "Password")
        i = 1

        prefix, suffix = data["prefix"], data["suffix"]
        user_list = []
        for number in range(data["number_from"], data["number_to"] + 1):
            raw_password = rand_str(data["password_length"])
            user = User(username=f"{prefix}{number}{suffix}", password=make_password(raw_password))
            user.raw_password = raw_password
            user_list.append(user)

        try:
            with transaction.atomic():

                ret = User.objects.bulk_create(user_list)
                UserProfile.objects.bulk_create([UserProfile(user=user) for user in ret])
                for item in user_list:
                    worksheet.write_string(i, 0, item.username)
                    worksheet.write_string(i, 1, item.raw_password)
                    i += 1
                workbook.close()
                return self.success({"file_id": file_id})
        except IntegrityError:
            # 원본은 DB 예외 메시지(DETAIL: Key (username)=(root11) already exists.)를
            # 그대로 돌려줬다. 읽히지도 않고 DB 내부 구조만 드러난다.
            return self.error("이미 사용 중인 사용자명이 있습니다")


class SchoolClassAdminAPI(APIView):
    """최고관리자 '수업' 탭: 모든 교사의 학급을 보고 고치고 지운다.

    최고관리자는 수업을 하지 않으므로 교사 화면 대신 여기서 살핀다.
    담당 교사를 바꾸는 길은 두지 않는다. 그 교사의 문제집·대회 배포가 학급을
    가리키고 있어서, 바꾸려면 교사 단위로 넘긴다(TeacherDataAPI.post).
    """
    @super_admin_required
    def get(self, request):
        class_id = request.GET.get("id")
        if class_id:
            school_class = self._class(class_id)
            if school_class is None:
                return self.error("학급이 존재하지 않습니다")
            # 집계(GROUP BY)가 붙으면 Meta 의 기본 정렬이 빠지므로 번호순을 직접 적는다
            students = school_class.memberships.select_related("student") \
                .annotate(submission_count=Count("student__submissions")).order_by("number")
            data = AdminSchoolClassSerializer(self._classes().get(id=school_class.id)).data
            data["problem_set_count"] = school_class.assignments.count()
            data["contest_count"] = school_class.contest_assignments.count()
            data["students"] = AdminClassStudentSerializer(students, many=True).data
            return self.success(data)

        classes = self._classes()
        teacher_id = int_or_none(request.GET.get("teacher_id"))
        if teacher_id:
            classes = classes.filter(teacher_id=teacher_id)
        archived = request.GET.get("archived")
        if archived in ("true", "false"):
            classes = classes.filter(is_archived=archived == "true")
        keyword = (request.GET.get("keyword") or "").strip()
        if keyword:
            classes = classes.filter(Q(school__name__icontains=keyword) | Q(teacher__username__icontains=keyword))
        classes = classes.order_by("-year", "school__name", "grade", "class_no", "teacher__username")
        data = self.paginate_data(request, classes, AdminSchoolClassSerializer)
        # 교사 고르기 칸. 학급이 있는 사람만이 아니라 지금 교사인 사람을 모두 보여준다.
        teachers = teacher_accounts().annotate(class_count=Count("classes")).order_by("username")
        data["teachers"] = [{"id": t.id, "username": t.username, "class_count": t.class_count}
                            for t in teachers]
        return self.success(data)

    @validate_serializer(EditSchoolClassSerializer)
    @super_admin_required
    def put(self, request):
        data = request.data
        school_class = self._class(data["id"])
        if school_class is None:
            return self.error("학급이 존재하지 않습니다")
        for field in ("year", "grade", "class_no", "is_archived"):
            if field in data:
                setattr(school_class, field, data[field])
        try:
            school_class.save()
        except IntegrityError:
            return self.error("그 선생님에게 같은 학급이 이미 있습니다")
        return self.success(AdminSchoolClassSerializer(self._classes().get(id=school_class.id)).data)

    @super_admin_required
    def delete(self, request):
        """학급과 소속 학생 계정을 지운다. 교사 화면의 학급 삭제와 같다."""
        school_class = self._class(request.GET.get("id"))
        if school_class is None:
            return self.error("학급이 존재하지 않습니다")
        return self.success({"deleted_students": delete_school_class(school_class)})

    @staticmethod
    def _classes():
        return SchoolClass.objects.select_related("school", "teacher") \
            .annotate(student_count=Count("memberships"))

    @staticmethod
    def _class(class_id):
        class_id = int_or_none(class_id)
        if class_id is None:
            return None
        return SchoolClass.objects.filter(id=class_id).first()
