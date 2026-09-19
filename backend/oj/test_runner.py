"""테스트가 실제 데이터 폴더에 닿지 못하게 막는 러너.

manage.py test 는 컨테이너 안에서 돌기 때문에(저장소의 pre-push 훅도 그렇게
한다) 테스트가 경로를 잘못 다루면 실제 그림과 테스트케이스가 사라진다.
실제로 그림 올리기 테스트가 /data/public/upload 를 통째로 지운 적이 있다.

그래서 두 가지를 한다.
1. 운영 설정에서는 아예 돌리지 않는다. 데이터베이스는 테스트용으로 따로 만들지만
   Redis 와 /data 는 운영과 같은 것을 쓴다 - 테스트를 돌릴 자리가 아니다.
2. 도는 동안 데이터 폴더를 임시 폴더로 바꿔 둔다. 코드가 경로를 모듈을 읽는
   시점이 아니라 쓸 때 settings 에서 꺼내므로 이렇게 바꿔치기할 수 있다.
"""
import os
import shutil
import tempfile

from django.conf import settings
from django.test.runner import DiscoverRunner

from utils.shortcuts import get_env

# 테스트가 파일을 만들고 지우는 폴더들
REDIRECTED_DIRS = ("UPLOAD_DIR", "AVATAR_UPLOAD_DIR", "TEST_CASE_DIR")


class SafeDataDirRunner(DiscoverRunner):
    def __init__(self, *args, **kwargs):
        if get_env("OJ_ENV", "dev") == "prod":
            raise SystemExit(
                "운영 설정(OJ_ENV=prod)에서는 테스트를 돌리지 않습니다.\n"
                "운영 컨테이너의 Redis 와 /data 를 그대로 쓰기 때문입니다. "
                "개발 컨테이너에서 돌려주세요."
            )
        super().__init__(*args, **kwargs)

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self.data_dir = tempfile.mkdtemp(prefix="oj-test-data-")
        for name in REDIRECTED_DIRS:
            path = os.path.join(self.data_dir, name.lower())
            os.makedirs(path)
            setattr(settings, name, path)

    def teardown_test_environment(self, **kwargs):
        super().teardown_test_environment(**kwargs)
        shutil.rmtree(self.data_dir, ignore_errors=True)
