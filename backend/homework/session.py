"""바로 과제 학생을 알아보는 출입증.

사이트 로그인(Django 세션)과 따로 둔다. 교사·학생 계정으로 로그인한 브라우저로
들어와도 과제에서 낸 것은 과제 참가자의 제출이 되고, 로그인 상태는 그대로다.

출입증은 참가자 id 를 서명한 쿠키다. 그 과제의 API(/api/hw/<코드>)에만 실려 가도록
경로를 좁힌다. 서버에 따로 저장하지 않으므로 기기를 바꿔 다시 들어와도 앞서 쓰던
기기의 출입증이 그대로 살아 있고, 참가자를 지우면(내보내기) 함께 무효가 된다.
"""
from django.conf import settings
from django.core import signing

from .models import HomeworkParticipant

COOKIE_NAME = "hw_participant"
COOKIE_SALT = "homework.participant"
# 과제가 며칠 열려 있어도 다시 들어오지 않고 이어서 풀 수 있을 만큼
COOKIE_MAX_AGE = 60 * 60 * 24 * 30


def cookie_path(homework):
    # 끝에 / 를 붙이지 않는다. 쿠키 경로 규칙상 /api/hw/123456 은 /api/hw/1234567 에
    # 실려 가지 않고, /api/hw/123456 과 그 아래에는 모두 실려 간다.
    return f"/api/hw/{homework.code}"


def issue(response, participant):
    response.set_cookie(COOKIE_NAME, signing.dumps(participant.id, salt=COOKIE_SALT),
                        max_age=COOKIE_MAX_AGE, path=cookie_path(participant.homework),
                        httponly=True, samesite="Lax", secure=settings.SESSION_COOKIE_SECURE)


def revoke(response, homework):
    response.delete_cookie(COOKIE_NAME, path=cookie_path(homework), samesite="Lax")


def current_participant(request, homework):
    """이 과제의 출입증을 가진 참가자. 없거나 다른 과제의 것이면 None."""
    value = request.COOKIES.get(COOKIE_NAME)
    if not value:
        return None
    try:
        participant_id = signing.loads(value, salt=COOKIE_SALT)
    except signing.BadSignature:
        return None
    return HomeworkParticipant.objects.select_related("homework", "user") \
        .filter(id=participant_id, homework=homework).first()
