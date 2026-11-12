# SheShop - 女性精品购物平台

基于 Django 的多商家购物平台，支持商家开店、商品管理、用户收藏下单和图片收集。

## 功能

**商家端**

- 注册开店，设置店铺名称、Logo、简介
- 管理商品类目（一级/二级分类）
- 发布商品，支持多图上传、价格、库存、详情
- 查看本店订单并更新状态
- 查看谁收藏了本店商品（含用户名）
- 接收用户上传的图片（含用户名、备注、时间）

**用户端**

- 用户名注册登录
- 按店铺浏览商品
- 收藏商品
- 下单购买（暂无支付环节）
- 向指定商家上传图片
- 仅能查看自己的收藏、订单和上传记录

## 技术栈

- Python 3.9+ / Django 4.2+
- PostgreSQL（生产）/ SQLite（开发）
- Bootstrap 5，响应式设计，适配手机端

## 快速开始

```bash
pip install -r requirements.txt

cp .env.example .env        # Windows 用 copy
# 编辑 .env，本地开发设 DB_ENGINE=sqlite 即可

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

访问 http://127.0.0.1:8000

使用流程：先注册商家账号 → 设置店铺 → 创建类目 → 添加商品 → 再注册普通用户体验购买。

## 配置

所有配置通过根目录 `.env` 文件管理，不需要改动代码。完整说明见 [DEPLOY.md](DEPLOY.md)。

常用配置项：

```ini
DEBUG=False                    # 生产环境必须关闭
SECRET_KEY=随机字符串
ALLOWED_HOSTS=your-domain.com

DB_ENGINE=postgresql           # postgresql 或 sqlite
DB_HOST=localhost              # 改成云数据库地址即可切换
DB_NAME=she_shop
DB_USER=sheshop
DB_PASSWORD=你的密码

FRONTEND_ASSETS=cdn            # cdn 或 local（离线部署）
MEDIA_ROOT=                    # 留空用项目目录
```

## 部署

Docker 一键启动（含 PostgreSQL）：

```bash
cp .env.example .env    # 修改 SECRET_KEY、DEBUG=False、密码
docker compose up -d
docker compose exec web python manage.py createsuperuser
```

其他部署方式（本地 PostgreSQL、云数据库、Nginx 配置、数据迁移）详见 [DEPLOY.md](DEPLOY.md)。

## 常用命令

```bash
python manage.py check_db        # 检查数据库连接配置
python manage.py migrate         # 执行数据库迁移
python manage.py collectstatic   # 收集静态文件（生产环境）

# SQLite 数据迁移到 PostgreSQL
python scripts/migrate_sqlite_to_postgres.py export
python scripts/migrate_sqlite_to_postgres.py import
```

## 目录结构

```
she_shop/
├── config/              # 项目配置
│   ├── settings.py      # 全部读取环境变量
│   ├── env_utils.py     # .env 加载与类型转换
│   └── urls.py
├── accounts/            # 用户与商家
├── shop/                # 商品、订单、收藏、图片收集
│   └── management/commands/check_db.py
├── templates/           # 页面模板
├── static/              # 静态资源
├── media/               # 用户上传文件（不提交 Git）
├── scripts/             # 数据迁移脚本
├── .env                 # 本地配置（不提交 Git）
├── .env.example         # 配置模板
├── Dockerfile
├── docker-compose.yml
└── DEPLOY.md            # 部署文档
```

## 注意

`.env` 包含密钥和数据库密码，已加入 `.gitignore`，请勿提交到仓库。
