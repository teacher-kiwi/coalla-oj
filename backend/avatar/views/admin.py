from django.utils.timezone import now

from account.decorators import avatar_manager_required
from account.models import AdminType
from utils.api import APIView, validate_serializer

from ..models import AvatarItem, OwnedItem
from ..serializers import AvatarItemSerializer, EditAvatarItemSerializer


def buyers(item):
    """코인을 내고 산 사람. 최고관리자는 사지 않고 입으므로 세지 않는다."""
    return item.owners.exclude(user__admin_type=AdminType.SUPER_ADMIN)


def drop_admin_copies(item):
    """최고관리자가 입으려고 넣어 둔 것을 치운다(코인을 내지 않았으니 돌려줄 것도 없다)"""
    OwnedItem.objects.filter(item=item, user__admin_type=AdminType.SUPER_ADMIN).delete()


class AvatarItemAdminAPI(APIView):
    """캐릭터 아이템 관리. 최고관리자, 또는 캐릭터 권한을 받은 관리자가 쓴다."""

    @avatar_manager_required
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
    @avatar_manager_required
    def post(self, request):
        data = request.data
        data.pop("id", None)
        item = AvatarItem.objects.create(created_by=request.user, **data,
                                         published_time=now() if data.get("visible") else None)
        return self.success(AvatarItemSerializer(item).data)

    @validate_serializer(EditAvatarItemSerializer)
    @avatar_manager_required
    def put(self, request):
        data = request.data
        try:
            item = AvatarItem.objects.get(id=data.pop("id", None))
        except (AvatarItem.DoesNotExist, TypeError, ValueError):
            return self.error("아이템이 없습니다")
        # 산 사람이 입고 있는 자리가 꼬이지 않게, 산 사람이 있으면 자리·종류는 그대로 둔다
        if (data["slot"], data["variant"]) != (item.slot, item.variant):
            if buyers(item).exists():
                return self.error("산 사람이 있는 아이템은 종류를 바꿀 수 없습니다")
            drop_admin_copies(item)
        for k, v in data.items():
            setattr(item, k, v)
        if item.visible and not item.published_time:
            item.published_time = now()
        item.save()
        return self.success(AvatarItemSerializer(item).data)

    @avatar_manager_required
    def delete(self, request):
        try:
            item = AvatarItem.objects.get(id=request.GET.get("id") or 0)
        except (AvatarItem.DoesNotExist, ValueError):
            return self.error("아이템이 없습니다")
        # 산 사람이 있으면 지우지 않고 샵에서 내린다. 산 사람은 계속 입을 수 있다.
        if buyers(item).exists():
            item.visible = False
            item.save(update_fields=["visible", "last_update_time"])
            return self.success({"hidden": True})
        drop_admin_copies(item)
        item.delete()
        return self.success({"hidden": False})
