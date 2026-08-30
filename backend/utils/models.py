# JSONField 를 여기서 다시 내보내는 이유: 옛 마이그레이션들이 utils.models.JSONField
# 를 가리키고 있어 경로를 유지해야 한다.
from django.db.models import JSONField  # NOQA
