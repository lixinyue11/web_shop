# ============ SheShop 应用镜像 ============
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

WORKDIR /app

# netcat 供 entrypoint 探测数据库端口
# psycopg2-binary 和 Pillow 都是预编译 wheel，无需 gcc 等编译工具链
RUN apt-get update && apt-get install -y --no-install-recommends \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# 先装依赖，利用 Docker 层缓存，代码变动时无需重装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# 以非 root 用户运行，上传文件不会产生 root 属主
RUN useradd -m -u 1000 app \
    && mkdir -p /app/media /app/staticfiles /app/logs \
    && chown -R app:app /app
USER app

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application"]
