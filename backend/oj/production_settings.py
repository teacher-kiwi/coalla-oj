from utils.shortcuts import get_env

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'HOST': get_env("POSTGRES_HOST", "postgres"),
        'PORT': get_env("POSTGRES_PORT", "5432"),
        'NAME': get_env("POSTGRES_DB"),
        'USER': get_env("POSTGRES_USER"),
        'PASSWORD': get_env("POSTGRES_PASSWORD")
    }
}

REDIS_CONF = {
    "host": get_env("REDIS_HOST", "redis"),
    "port": get_env("REDIS_PORT", "6379")
}

DEBUG = False

ALLOWED_HOSTS = ['*']

# Django 4 는 CSRF 검증 시 Origin 헤더를 Host 와 대조한다.
# 리버스 프록시가 Host 를 그대로 넘기면 추가 설정이 필요 없지만,
# 그렇지 않은 구성(CDN, 다중 도메인 등)에서는 여기에 오리진을 등록해야 한다.
#   예: CSRF_TRUSTED_ORIGINS=https://oj.example.kr,https://www.example.kr
_csrf_origins = get_env("CSRF_TRUSTED_ORIGINS", "")
if _csrf_origins:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(",") if o.strip()]

DATA_DIR = "/data"
