# SheShop 部署指南

本项目所有可变配置集中在 `.env` 文件，切换数据库、域名、存储路径都无需改动代码。

---

## 配置总览

复制 `.env.example` 为 `.env` 后按需修改。关键变量说明：

| 变量 | 作用 | 本地开发 | 生产环境 |
|------|------|---------|---------|
| `SECRET_KEY` | Django 密钥 | 默认值即可 | **必须改为随机值** |
| `DEBUG` | 调试模式 | `True` | **必须为 `False`** |
| `ALLOWED_HOSTS` | 允许的域名 | `127.0.0.1,localhost` | 你的域名 |
| `DB_ENGINE` | 数据库类型 | `sqlite` 或 `postgresql` | `postgresql` |
| `DB_HOST` | 数据库地址 | `localhost` | 云数据库地址 |
| `DB_SSLMODE` | SSL 模式 | `prefer` | 云数据库通常需 `require` |
| `MEDIA_ROOT` | 上传文件目录 | 留空用项目目录 | 独立磁盘路径 |
| `FRONTEND_ASSETS` | 前端资源 | `cdn` | `cdn` 或 `local`（离线） |

生成随机密钥：

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

---

## 方式一：本地开发（SQLite）

最快上手，无需安装数据库。

```bash
cd she_shop
pip install -r requirements.txt

copy .env.example .env     # Windows
# cp .env.example .env     # Linux/Mac

# .env 中设置 DB_ENGINE=sqlite

python manage.py migrate
python manage.py runserver
```

访问 http://127.0.0.1:8000

---

## 方式二：本地 PostgreSQL

### 1. 安装并创建数据库

```sql
CREATE DATABASE she_shop ENCODING 'UTF8';
CREATE USER sheshop WITH PASSWORD '你的密码';
GRANT ALL PRIVILEGES ON DATABASE she_shop TO sheshop;

-- PostgreSQL 15+ 还需要授权 schema
\c she_shop
GRANT ALL ON SCHEMA public TO sheshop;
```

### 2. 修改 `.env`

```ini
DB_ENGINE=postgresql
DB_NAME=she_shop
DB_USER=sheshop
DB_PASSWORD=你的密码
DB_HOST=localhost
DB_PORT=5432
```

### 3. 验证并启动

```bash
python manage.py check_db      # 检查连接是否正常
python manage.py migrate
python manage.py runserver
```

生产环境（`DEBUG=False`）还必须执行一次静态文件收集，否则所有页面会报 500：

```bash
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

---

## 方式三：Docker 一键部署（推荐）

包含 PostgreSQL，适合服务器部署。

```bash
# 1. 准备配置
cp .env.example .env
# 修改 .env：SECRET_KEY、DEBUG=False、ALLOWED_HOSTS、POSTGRES_PASSWORD

# 2. 启动
docker compose up -d

# 3. 创建管理员
docker compose exec web python manage.py createsuperuser
```

常用命令：

```bash
docker compose logs -f web        # 查看日志
docker compose restart web        # 重启应用
docker compose down               # 停止（数据保留）
docker compose down -v            # 停止并删除数据卷（数据清空）
```

---

## 方式四：使用云数据库

阿里云 RDS、腾讯云 PostgreSQL、Supabase、Neon 等均适用。

### 1. 修改 `.env`

```ini
DB_ENGINE=postgresql
DB_HOST=pgm-xxxxx.pg.rds.aliyuncs.com   # 云厂商提供的地址
DB_PORT=5432
DB_NAME=she_shop
DB_USER=你的用户名
DB_PASSWORD=你的密码
DB_SSLMODE=require                       # 云数据库通常强制 SSL
DB_CONN_MAX_AGE=60                       # 复用连接，减少远程握手开销
```

### 2. 云厂商控制台需完成

- 白名单添加服务器公网 IP
- 确认实例已开启公网访问（或使用内网地址，延迟更低）

### 3. 如果同时用 Docker

注释掉 `docker-compose.yml` 中整个 `db:` 服务块，以及 `web` 服务的 `depends_on`，并删除 `web.environment` 里覆盖 `DB_HOST` 的那几行，让它直接读 `.env`。

---

## 从 SQLite 迁移已有数据到 PostgreSQL

本地已有数据时使用。

```bash
# 1. 确保 .env 中 DB_ENGINE=sqlite，导出数据
python scripts/migrate_sqlite_to_postgres.py export

# 2. 修改 .env：DB_ENGINE=postgresql，填好连接参数

# 3. 在新库建表
python manage.py check_db
python manage.py migrate

# 4. 导入数据
python scripts/migrate_sqlite_to_postgres.py import
```

媒体文件需单独复制：把 `media/` 目录整个传到新服务器对应位置。

---

## 生产环境检查清单

部署前逐项确认：

- [ ] `SECRET_KEY` 已改为随机值，且未提交到 Git
- [ ] `DEBUG=False`
- [ ] `ALLOWED_HOSTS` 填写实际域名，不要留 `*`
- [ ] 数据库密码足够复杂
- [ ] `.env` 文件未被提交（`git status` 确认）
- [ ] 配置 HTTPS 后，设置 `SECURE_SSL_REDIRECT=True`、`SESSION_COOKIE_SECURE=True`、`CSRF_COOKIE_SECURE=True`
- [ ] 使用 Nginx 时设置 `USE_X_FORWARDED_PROTO=True`
- [ ] `LOG_TO_FILE=True` 开启文件日志
- [ ] 已执行 `python manage.py collectstatic`
- [ ] 数据库定期备份

备份命令：

```bash
# 本地 PostgreSQL
pg_dump -U sheshop she_shop > backup_$(date +%Y%m%d).sql

# Docker 环境
docker compose exec db pg_dump -U sheshop she_shop > backup.sql
```

---

## Nginx 反向代理示例

```nginx
server {
    listen 80;
    server_name shop.example.com;

    client_max_body_size 20M;   # 需大于 MAX_UPLOAD_SIZE

    location /static/ {
        alias /path/to/she_shop/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /path/to/she_shop/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

配合 Nginx 时，`.env` 中设置 `SERVE_MEDIA=False`、`USE_X_FORWARDED_PROTO=True`。

---

## 常见问题

**连接数据库失败**

先运行 `python manage.py check_db`，会输出当前配置和具体错误原因。常见原因：服务未启动、密码错误、数据库未创建、防火墙未放行。

**页面样式丢失**

检查 `FRONTEND_ASSETS` 设置。设为 `cdn` 需要联网，这是默认值。

设为 `local`（离线部署）前，必须先把以下文件放进对应目录，否则 `DEBUG=False` 时会直接 500：

| 文件 | 放置位置 |
|------|---------|
| `bootstrap.min.css` | `static/css/` |
| `bootstrap-icons.min.css` | `static/css/` |
| `bootstrap.bundle.min.js` | `static/js/` |
| 图标字体文件 | `static/fonts/` |

放好后执行 `python manage.py collectstatic` 再启动。

**上传的图片看不到**

`DEBUG=False` 时 Django 默认不提供媒体文件服务。要么配置 Nginx，要么在 `.env` 中设置 `SERVE_MEDIA=True`。

**上传大图片失败**

调大 `.env` 中的 `MAX_UPLOAD_SIZE`，Nginx 的 `client_max_body_size` 也要同步调大。
