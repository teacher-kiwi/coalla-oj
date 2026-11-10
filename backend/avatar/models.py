"""도트 캐릭터 아이템. 사이트 관리자만 만든다(관리자 페이지의 캐릭터 공방).

그림은 부위마다 칸 하나를 글자 하나로 적은 문자열이다('.' 빈칸, 그 뒤 64글자가 팔레트
1~64번). 프런트엔드 utils/character.js 의 CODE·PART 와 반드시 같아야 한다.
팔레트 순서를 바꾸면 저장된 모든 아이템의 색이 바뀐다.
"""
from django.db import models

from account.models import User

CODE = ".abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/"

# 부위: (가로, 세로)
PART_SIZE = {
    "head": (40, 36),
    "torso": (24, 18),
    "armL": (10, 16),
    "armR": (10, 16),
    "legL": (11, 16),
    "legR": (11, 16),
    "skirt": (26, 16),
}


class AvatarSlot:
    HAIR = "hair"
    HAT = "hat"
    FACE = "face"
    ACC = "acc"
    TOP = "top"
    BOTTOM = "bottom"
    SHOES = "shoes"


# 자리마다 고를 수 있는 종류. 첫 값이 기본이다. 빈 목록이면 종류가 없다.
SLOT_VARIANTS = {
    AvatarSlot.HAIR: [],
    AvatarSlot.HAT: ["top", "full", "none"],
    AvatarSlot.FACE: [],
    AvatarSlot.ACC: [],
    AvatarSlot.TOP: [],
    AvatarSlot.BOTTOM: ["pants", "skirt"],
    AvatarSlot.SHOES: ["low", "boots"],
}


def parts_for(slot, variant):
    """이 자리·종류의 아이템이 그리는 부위"""
    if slot == AvatarSlot.BOTTOM:
        return ["skirt"] if variant == "skirt" else ["legL", "legR"]
    if slot == AvatarSlot.TOP:
        return ["torso", "armL", "armR"]
    if slot == AvatarSlot.SHOES:
        return ["legL", "legR"]
    return ["head"]


class AvatarItem(models.Model):
    name = models.CharField(max_length=30)
    slot = models.CharField(max_length=10)
    # 모자: top/full/none, 하의: pants/skirt, 신발: low/boots, 나머지는 빈 값
    variant = models.CharField(max_length=10, blank=True, default="")
    # {"head": "....abc..."} 부위마다 가로×세로 길이의 문자열
    parts = models.JSONField(default=dict)
    price = models.PositiveIntegerField(default=50)
    # 샵에 내놓았는가. 꺼 두면 관리자 화면에서만 보인다.
    visible = models.BooleanField(default=False)
    # 샵에 처음 올린 시각. 샵의 최신순 정렬과 'NEW' 표시에 쓴다. 내렸다 다시 올려도 바꾸지 않는다.
    published_time = models.DateTimeField(null=True, blank=True)
    # 디자이너 이름(선택). 나중에 학생 작품을 올릴 때 이름을 밝히는 데 쓴다.
    designer = models.CharField(max_length=30, blank=True, default="")
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    create_time = models.DateTimeField(auto_now_add=True)
    last_update_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "avatar_item"
        ordering = ("-id",)


class OwnedItem(models.Model):
    """학생이 산 아이템. equipped 면 지금 입고 있다(자리마다 하나)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="avatar_items")
    # 산 사람이 있는 아이템은 지우지 않고 샵에서 내린다(관리자 삭제 참고)
    item = models.ForeignKey(AvatarItem, on_delete=models.PROTECT, related_name="owners")
    equipped = models.BooleanField(default=False)
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "avatar_owned_item"
        ordering = ("-id",)
        constraints = [
            models.UniqueConstraint(fields=["user", "item"], name="avatar_owned_once"),
        ]


class CoinReason:
    SOLVE = "solve"      # 연습 문제를 처음 맞힘. ref = 문제 id
    ATTEND = "attend"    # 그날 첫 접속. ref = 한국 날짜(YYYY-MM-DD)
    BUY = "buy"          # 샵에서 아이템을 삼(금액은 음수). ref = 아이템 id


class CoinLog(models.Model):
    """코인 원장. 잔액은 따로 두지 않고 이 표의 합으로 센다.

    (사용자, 이유, 대상)이 겹치지 않아서 같은 문제·같은 날에 두 번 받을 수 없다.
    재채점이나 동시에 들어온 채점이 같은 정답을 두 번 처리해도 한 번만 들어간다.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="coin_logs")
    amount = models.IntegerField()
    reason = models.CharField(max_length=10)
    ref = models.CharField(max_length=64)
    # 정답 코인을 준 제출. 채점 결과 화면이 "+10 코인"을 띄울 때 찾는다.
    submission_id = models.CharField(max_length=32, blank=True, default="", db_index=True)
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "coin_log"
        ordering = ("-id",)
        constraints = [
            models.UniqueConstraint(fields=["user", "reason", "ref"], name="coin_log_once"),
        ]
