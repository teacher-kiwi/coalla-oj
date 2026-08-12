from rest_framework import serializers


class UsernameSerializer(serializers.Serializer):
    """공개 화면에 사용자를 표시할 때 쓴다(순위, 대회 순위 등).

    username 은 계정 식별자를 그대로 내보내지 않고 표시용 이름을 계산해서 넣는다.
    수업용 학생 계정의 내부 아이디(예: kim3-01)가 노출되면
    학교·학년·반·번호가 그대로 드러나기 때문이다.
    """
    id = serializers.IntegerField()
    username = serializers.SerializerMethodField()
    real_name = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        self.need_real_name = kwargs.pop("need_real_name", False)
        super().__init__(*args, **kwargs)

    def get_username(self, obj):
        # 순환 임포트를 피하려고 지역 임포트한다
        from account.models import public_display_name
        return public_display_name(obj)

    def get_real_name(self, obj):
        return obj.userprofile.real_name if self.need_real_name else None
