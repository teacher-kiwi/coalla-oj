import logging
import dramatiq

from options.options import SysOptions
from utils.shortcuts import send_email, DRAMATIQ_WORKER_ARGS

logger = logging.getLogger(__name__)


@dramatiq.actor(**DRAMATIQ_WORKER_ARGS(max_retries=3))
def send_email_async(from_name, to_email, to_name, subject, content):
    if not SysOptions.smtp_config:
        return
    try:
        send_email(smtp_config=SysOptions.smtp_config,
                   from_name=from_name,
                   to_email=to_email,
                   to_name=to_name,
                   subject=subject,
                   content=content)
    except Exception as e:
        logger.exception(e)


@dramatiq.actor(**DRAMATIQ_WORKER_ARGS())
def sync_schools_async():
    """나이스에서 전국 학교 목록을 내려받아 저장한다.

    1만 건이 넘고 페이지마다 API 를 호출하므로 몇 분이 걸린다.
    진행 상황은 SysOptions.school_sync_status 에 기록해 관리자 화면에서 볼 수 있게 한다.
    """
    from django.utils.timezone import now
    from .neis import NeisError, set_status, sync_schools

    set_status(state="running", processed=0, total=0, message="", finished_at=None)
    try:
        def progress(processed, total):
            set_status(state="running", processed=processed, total=total)

        saved = sync_schools(SysOptions.neis_api_key, progress=progress)
        set_status(state="done", saved=saved, message="",
                   finished_at=now().isoformat())
        # 루트 로거가 WARNING 이라 info 는 출력되지 않는다. 운영 확인용이므로 warning 으로 남긴다.
        logger.warning("나이스 학교 적재 완료: %s 건", saved)
    except NeisError as e:
        set_status(state="failed", message=str(e), finished_at=now().isoformat())
        logger.error("나이스 학교 적재 실패: %s", e)
    except Exception as e:
        set_status(state="failed", message=f"{type(e).__name__}: {e}"[:300],
                   finished_at=now().isoformat())
        logger.exception(e)
