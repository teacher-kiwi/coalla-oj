from account.decorators import super_admin_required
from utils.api import APIView, validate_serializer

from ..models import AvatarItem
from ..serializers import AvatarItemSerializer, EditAvatarItemSerializer


class AvatarItemAdminAPI(APIView):
    """캐릭터 아이템 관리. 사이트 관리자(최고관리자)만 쓴다."""

    @super_admin_required
    def get(self, request):
        item_id = request.GET.get("id")
        if item_id:
            try:
                return self.success(AvatarItemSerializer(AvatarItem.objects.get(id=item_id)).data)
            except (AvatarItem.DoesNotExist, ValueError):
                return self.error("아이템이 없습니다")
        # 아이템은 많아야 수백 개라 한 번에 준다. 목록 화면이 그림을 그려야 해서 parts 도 싣는다.
        return self.success(AvatarItemSerializer(AvatarItem.objects.all(), many=True).data)

    @validate_serializer(EditAvatarItemSerializer)
    @super_admin_required
    def post(self, request):
        data = request.data
        data.pop("id", None)
        item = AvatarItem.objects.create(created_by=request.user, **data)
        return self.success(AvatarItemSerializer(item).data)

    @validate_serializer(EditAvatarItemSerializer)
    @super_admin_required
    def put(self, request):
        data = request.data
        try:
            item = AvatarItem.objects.get(id=data.pop("id", None))
        except (AvatarItem.DoesNotExist, TypeError, ValueError):
            return self.error("아이템이 없습니다")
        # 산 사람이 입고 있는 자리가 꼬이지 않게, 산 사람이 있으면 자리·종류는 그대로 둔다
        if (data["slot"], data["variant"]) != (item.slot, item.variant) and item.owners.exists():
            return self.error("산 사람이 있는 아이템은 종류를 바꿀 수 없습니다")
        for k, v in data.items():
            setattr(item, k, v)
        item.save()
        return self.success(AvatarItemSerializer(item).data)

    @super_admin_required
    def delete(self, request):
        try:
            item = AvatarItem.objects.get(id=request.GET.get("id") or 0)
        except (AvatarItem.DoesNotExist, ValueError):
            return self.error("아이템이 없습니다")
        # 산 사람이 있으면 지우지 않고 샵에서 내린다. 산 사람은 계속 입을 수 있다.
        if item.owners.exists():
            item.visible = False
            item.save(update_fields=["visible", "last_update_time"])
            return self.success({"hidden": True})
        item.delete()
        return self.success({"hidden": False})
