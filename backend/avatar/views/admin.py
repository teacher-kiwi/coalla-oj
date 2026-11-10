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
        for k, v in data.items():
            setattr(item, k, v)
        item.save()
        return self.success(AvatarItemSerializer(item).data)

    @super_admin_required
    def delete(self, request):
        # 4단계(샵)에서 산 사람이 생기면, 산 아이템은 지우지 말고 샵에서 내리게 바꾼다
        AvatarItem.objects.filter(id=request.GET.get("id") or 0).delete()
        return self.success()
