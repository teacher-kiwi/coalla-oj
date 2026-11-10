from django.db import transaction
from django.db.models import Q

from account.decorators import login_required
from account.models import AdminType
from problem.models import Problem
from utils.api import APIView, validate_serializer

from ..coins import BuyError, balance, buy
from ..models import SLOT_VARIANTS, AvatarItem, CoinLog, CoinReason, OwnedItem
from ..serializers import BuySerializer, EquipSerializer, ShopItemSerializer

# 한 번에 모습을 물어볼 수 있는 사람 수. 순위표 한 쪽(최대 100명)이 들어가야 한다.
LOOKS_LIMIT = 100


def equipped_of(user_id):
    return dict(OwnedItem.objects.filter(user_id=user_id, equipped=True).values_list("item__slot", "item_id"))


class CoinLogAPI(APIView):
    """내 코인 잔액과 내역"""

    @login_required
    def get(self, request):
        logs = CoinLog.objects.filter(user=request.user)
        data = self.paginate_data(request, logs)
        page = list(data["results"])

        # 정답 코인은 어느 문제였는지, 구매는 어느 아이템이었는지 이름을 붙인다
        def ids(reason):
            return [int(log.ref) for log in page if log.reason == reason and log.ref.isdigit()]
        names = {
            CoinReason.SOLVE: dict(Problem.objects.filter(id__in=ids(CoinReason.SOLVE)).values_list("id", "title")),
            CoinReason.BUY: dict(AvatarItem.objects.filter(id__in=ids(CoinReason.BUY)).values_list("id", "name")),
        }
        data["results"] = [{
            "id": log.id, "amount": log.amount, "reason": log.reason, "ref": log.ref,
            "title": names.get(log.reason, {}).get(int(log.ref)) if log.ref.isdigit() else None,
            "create_time": log.create_time.isoformat(),
        } for log in page]
        data["balance"] = balance(request.user.id)
        return self.success(data)


class ShopAPI(APIView):
    """샵 목록. 샵에 올린 아이템과, 샵에서 내렸어도 내가 가진 아이템.

    최고관리자는 샵에 안 올린 것까지 모든 아이템을 사지 않고 입는다(wear_all).
    """

    @login_required
    def get(self, request):
        user = request.user
        if user.is_super_admin():
            items = AvatarItem.objects.all()
            return self.success({
                "items": ShopItemSerializer(items, many=True).data,
                "owned": [i.id for i in items],
                "hidden": [i.id for i in items if not i.visible],
                "equipped": equipped_of(user.id),
                "balance": balance(user.id),
                "can_buy": False,
                "wear_all": True,
            })
        owned = list(OwnedItem.objects.filter(user=user).values_list("item_id", flat=True))
        items = AvatarItem.objects.filter(Q(visible=True) | Q(id__in=owned))
        return self.success({
            "items": ShopItemSerializer(items, many=True).data,
            "owned": owned,
            "hidden": [],
            "equipped": equipped_of(user.id),
            "balance": balance(user.id),
            "can_buy": user.admin_type != AdminType.GUEST,
            "wear_all": False,
        })


class BuyAPI(APIView):
    @validate_serializer(BuySerializer)
    @login_required
    def post(self, request):
        try:
            item = AvatarItem.objects.get(id=request.data["item_id"])
        except AvatarItem.DoesNotExist:
            return self.error("아이템이 없습니다")
        try:
            left = buy(request.user, item)
        except BuyError as e:
            return self.error(str(e))
        return self.success({"balance": left, "equipped": equipped_of(request.user.id)})


class EquipAPI(APIView):
    """입을 옷 한 벌을 통째로 저장한다. 가진 아이템만 입을 수 있다."""

    @validate_serializer(EquipSerializer)
    @login_required
    def put(self, request):
        user = request.user
        want = {slot: item_id for slot, item_id in request.data["equip"].items() if item_id}
        if any(slot not in SLOT_VARIANTS for slot in want):
            return self.error("아이템 자리가 올바르지 않습니다")
        if user.is_super_admin():
            # 최고관리자는 사지 않고 입는다. 입을 때 코인 없이 '가진 아이템'으로 넣어 둔다.
            have = set(OwnedItem.objects.filter(user=user).values_list("item_id", flat=True))
            OwnedItem.objects.bulk_create(
                [OwnedItem(user=user, item=item) for item in AvatarItem.objects.filter(id__in=want.values())
                 if item.id not in have], ignore_conflicts=True)
        owned = {o.item_id: o for o in OwnedItem.objects.filter(user=user, item_id__in=want.values())
                 .select_related("item")}
        for slot, item_id in want.items():
            if item_id not in owned:
                return self.error("가지지 않은 아이템은 입을 수 없습니다")
            if owned[item_id].item.slot != slot:
                return self.error("아이템 자리가 맞지 않습니다")
        with transaction.atomic():
            OwnedItem.objects.filter(user=user, equipped=True).update(equipped=False)
            OwnedItem.objects.filter(user=user, item_id__in=want.values()).update(equipped=True)
        return self.success({"equipped": equipped_of(user.id)})


class LooksAPI(APIView):
    """여러 사람이 입은 아이템. 순위표·채점 현황 같은 공개 화면이 캐릭터를 그릴 때 쓴다.

    ?usernames=a,b,c → {"looks": {아이디: {자리: 아이템 id}}, "items": {id: 아이템}}
    아이템이 없는 사람은 looks 에 빠진다(기본 모습).
    """

    def get(self, request):
        names = [n for n in request.GET.get("usernames", "").split(",") if n][:LOOKS_LIMIT]
        looks = {}
        item_ids = set()
        rows = OwnedItem.objects.filter(user__username__in=names, equipped=True) \
            .values_list("user__username", "item__slot", "item_id")
        for username, slot, item_id in rows:
            looks.setdefault(username, {})[slot] = item_id
            item_ids.add(item_id)
        items = ShopItemSerializer(AvatarItem.objects.filter(id__in=item_ids), many=True).data
        return self.success({"looks": looks, "items": {i["id"]: i for i in items}})
