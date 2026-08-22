from rest_framework import serializers


class UsernameSerializer(serializers.Serializer):
    """공개 화면에 사용자를 표시할 때 쓴다(순위, 대회 순위 등).

    학생 계정 아이디는 무작위라("학생12345678") 학급도 번호도 드러나지 않는다.
    그래서 아이디를 그대로 내보낸다. 예전에는 "○○학교 학생"으로 감췄는데,
    그 방식은 학교를 노출하면서도 학생끼리 구분은 안 되는 절충이었다.

    담당 교사가 볼 때만 nickname 을 함께 실어 자기 학생을 알아보게 한다.
    """
    id = serializers.IntegerField()
    username = serializers.CharField()
    nickname = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        # {student_id: nickname}. 담당 교사가 목록을 볼 때만 채워서 넘긴다.
        self.nicknames = kwargs.pop("nicknames", None) or {}
        super().__init__(*args, **kwargs)

    def get_nickname(self, obj):
        return self.nicknames.get(obj.id)
