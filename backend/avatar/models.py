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
    # 디자이너 이름(선택). 나중에 학생 작품을 올릴 때 이름을 밝히는 데 쓴다.
    designer = models.CharField(max_length=30, blank=True, default="")
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    create_time = models.DateTimeField(auto_now_add=True)
    last_update_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "avatar_item"
        ordering = ("-id",)
