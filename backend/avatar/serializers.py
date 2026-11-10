from utils.api import serializers

from .models import CODE, PART_SIZE, SLOT_VARIANTS, AvatarItem, parts_for


class AvatarItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvatarItem
        fields = ("id", "name", "slot", "variant", "parts", "price", "visible", "designer",
                  "create_time", "last_update_time")


class ShopItemSerializer(serializers.ModelSerializer):
    """학생 화면용. 샵 공개 여부·만든 사람은 싣지 않는다."""
    class Meta:
        model = AvatarItem
        fields = ("id", "name", "slot", "variant", "parts", "price", "designer", "last_update_time")


class BuySerializer(serializers.Serializer):
    item_id = serializers.IntegerField()


class EquipSerializer(serializers.Serializer):
    # {자리: 아이템 id 또는 null}. 빠진 자리는 벗는다.
    equip = serializers.DictField(child=serializers.IntegerField(allow_null=True))


class EditAvatarItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    name = serializers.CharField(max_length=30, error_messages={
        "blank": "아이템 이름을 적어주세요", "max_length": "이름은 30자까지입니다"})
    slot = serializers.ChoiceField(choices=list(SLOT_VARIANTS), error_messages={
        "invalid_choice": "아이템 종류가 올바르지 않습니다"})
    variant = serializers.CharField(max_length=10, allow_blank=True, required=False, default="")
    parts = serializers.DictField(child=serializers.CharField(allow_blank=False))
    price = serializers.IntegerField(min_value=0, max_value=10000, error_messages={
        "min_value": "가격은 0 이상이어야 합니다", "max_value": "가격은 10000 이하여야 합니다"})
    visible = serializers.BooleanField(default=False)
    designer = serializers.CharField(max_length=30, allow_blank=True, required=False, default="")

    def validate(self, data):
        slot = data["slot"]
        choices = SLOT_VARIANTS[slot]
        variant = data.get("variant") or ""
        if choices:
            variant = variant or choices[0]
            if variant not in choices:
                raise serializers.ValidationError("아이템 세부 종류가 올바르지 않습니다")
        elif variant:
            raise serializers.ValidationError("이 아이템 종류에는 세부 종류가 없습니다")
        data["variant"] = variant

        allowed = parts_for(slot, variant)
        parts = data["parts"]
        if set(parts) != set(allowed):
            needed = ", ".join(allowed)
            raise serializers.ValidationError(f"부위가 맞지 않습니다. 필요한 부위: {needed}")
        painted = False
        for name, text in parts.items():
            w, h = PART_SIZE[name]
            if len(text) != w * h:
                raise serializers.ValidationError(f"{name} 그림의 크기가 맞지 않습니다")
            if any(ch not in CODE for ch in text):
                raise serializers.ValidationError(f"{name} 그림에 읽을 수 없는 글자가 있습니다")
            painted = painted or any(ch != "." for ch in text)
        if not painted:
            raise serializers.ValidationError("아직 아무것도 그리지 않았습니다")
        data["name"] = data["name"].strip()
        if not data["name"]:
            raise serializers.ValidationError("아이템 이름을 적어주세요")
        return data
