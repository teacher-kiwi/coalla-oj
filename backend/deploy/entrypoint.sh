#!/bin/sh

APP=/app
DATA=/data

mkdir -p $DATA/log $DATA/config $DATA/ssl $DATA/test_case $DATA/public/upload $DATA/public/avatar $DATA/public/website

if [ ! -f "$DATA/config/secret.key" ]; then
    echo $(cat /dev/urandom | head -1 | md5sum | head -c 32) > "$DATA/config/secret.key"
fi

if [ ! -f "$DATA/public/avatar/default.png" ]; then
    cp data/public/avatar/default.png $DATA/public/avatar
fi

if [ ! -f "$DATA/public/website/favicon.ico" ]; then
    cp data/public/website/favicon.ico $DATA/public/website
fi

if [ -z "$MAX_WORKER_NUM" ]; then
    export CPU_CORE_NUM=$(grep -c ^processor /proc/cpuinfo)
    if [ "$CPU_CORE_NUM" -lt 2 ]; then
        export MAX_WORKER_NUM=2
    else
        export MAX_WORKER_NUM=$(($CPU_CORE_NUM))
    fi
fi

cd $APP

# 최초 기동 시 마이그레이션 파일이 없으면 모델에서 생성한다.
# (마이그레이션을 리셋했으므로 이미지에 0001_initial 이 없을 수 있다)
python manage.py makemigrations account announcement conf contest options problem submission --no-input

if [ -z "$ADMIN_PASSWORD" ]; then
    ADMIN_PASSWORD=rootroot
    echo "!! ADMIN_PASSWORD 가 설정되지 않아 기본값을 사용합니다. 반드시 변경하세요 !!"
fi

n=0
while [ $n -lt 5 ]
do
    python manage.py migrate --no-input &&
    python manage.py inituser --username=root --password="$ADMIN_PASSWORD" --action=create_super_admin &&
    python manage.py seed_problem_tags &&
    echo "from options.options import SysOptions; SysOptions.judge_server_token='$JUDGE_SERVER_TOKEN'" | python manage.py shell &&
    echo "from conf.models import JudgeServer; JudgeServer.objects.update(task_number=0)" | python manage.py shell &&
    break
    n=$(($n+1))
    echo "Failed to migrate, going to retry..."
    sleep 8
done

addgroup -g 903 spj
adduser -u 900 -S -G spj server

chown -R server:spj $DATA
find $DATA/test_case -type d -exec chmod 710 {} \;
find $DATA/test_case -type f -exec chmod 640 {} \;

if [ "$OJ_ENV" = "prod" ]; then
    exec supervisord -c /app/deploy/supervisord.conf
else
    python manage.py rundramatiq --processes 1 --threads 4 &
    exec python manage.py runserver 0.0.0.0:8000
fi