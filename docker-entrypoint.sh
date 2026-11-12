#!/bin/sh
# 容器启动脚本：等待数据库就绪 -> 迁移 -> 收集静态文件 -> 启动服务
set -e

if [ "$DB_ENGINE" = "postgresql" ] || [ "$DB_ENGINE" = "postgres" ]; then
    echo "等待 PostgreSQL (${DB_HOST}:${DB_PORT}) 就绪..."

    RETRIES=30
    while ! nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null; do
        RETRIES=$((RETRIES - 1))
        if [ $RETRIES -le 0 ]; then
            echo "数据库连接超时，请检查 DB_HOST / DB_PORT 配置"
            exit 1
        fi
        sleep 2
    done

    echo "PostgreSQL 已就绪"
fi

echo "执行数据库迁移..."
python manage.py migrate --noinput

echo "收集静态文件..."
python manage.py collectstatic --noinput

# 默认参数为 gunicorn 时，补上可通过环境变量调节的运行参数
if [ "$1" = "gunicorn" ]; then
    exec "$@" \
        --bind "0.0.0.0:${GUNICORN_PORT:-8000}" \
        --workers "${GUNICORN_WORKERS:-3}" \
        --timeout "${GUNICORN_TIMEOUT:-120}" \
        --access-logfile -
fi

exec "$@"
