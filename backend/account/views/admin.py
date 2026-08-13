import os
import re
import xlsxwriter

from django.db import transaction, IntegrityError
from django.db.models import Q
from django.http import HttpResponse
from django.contrib.auth.hashers import make_password

from submission.models import Submission
from utils.api import APIView, validate_serializer
from utils.shortcuts import rand_str

from ..decorators import super_admin_required
from ..models import AdminType, ProblemPermission, User, UserProfile
from ..serializers import EditUserSerializer, UserAdminSerializer, GenerateUserSerializer
from ..serializers import ImportUserSeralizer


class UserAdminAPI(APIView):
    @validate_serializer(ImportUserSeralizer)
    @super_admin_required
    def post(self, request):
        data = request.data["users"]

        user_list = []
        for user_data in data:
            if len(user_data) != 4 or len(user_data[0]) > 32:
                return self.error(f"데이터 처리 중 오류가 발생했습니다: '{user_data}'")
            user_list.append(User(username=user_data[0], password=make_password(user_data[1]), email=user_data[2]))

        try:
            with transaction.atomic():
                ret = User.objects.bulk_create(user_list)
                UserProfile.objects.bulk_create([UserProfile(user=ret[i], real_name=data[i][3]) for i in range(len(ret))])
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
        if User.objects.filter(username=data["username"].lower()).exclude(id=user.id).exists():
            return self.error("이미 사용 중인 사용자명입니다")
        if User.objects.filter(email=data["email"].lower()).exclude(id=user.id).exists():
            return self.error("이미 사용 중인 이메일입니다")

        pre_username = user.username
        user.username = data["username"].lower()
        user.email = data["email"].lower()
        user.admin_type = data["admin_type"]
        user.is_disabled = data["is_disabled"]

        if data["admin_type"] == AdminType.ADMIN:
            user.problem_permission = data["problem_permission"]
        elif data["admin_type"] == AdminType.SUPER_ADMIN:
            user.problem_permission = ProblemPermission.ALL
        else:
            user.problem_permission = ProblemPermission.NONE

        if data["password"]:
            user.set_password(data["password"])

        user.save()
        if pre_username != user.username:
            Submission.objects.filter(username=pre_username).update(username=user.username)

        UserProfile.objects.filter(user=user).update(real_name=data["real_name"])
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

        user = User.objects.all().order_by("-create_time")

        keyword = request.GET.get("keyword", None)
        if keyword:
            user = user.filter(Q(username__icontains=keyword) |
                               Q(userprofile__real_name__icontains=keyword) |
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
        User.objects.filter(id__in=ids).delete()
        return self.success()


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

        user_list = []
        for number in range(data["number_from"], data["number_to"] + 1):
            raw_password = rand_str(data["password_length"])
            user = User(username=f"{data['prefix']}{number}{data['suffix']}", password=make_password(raw_password))
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
