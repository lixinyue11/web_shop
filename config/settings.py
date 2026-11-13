"""
SheShop 女性购物平台 - Django 配置

所有可变配置均通过环境变量控制，见项目根目录 .env 文件。
本地开发复制 .env.example 为 .env 并按需修改即可。
"""
from pathlib import Path

from .env_utils import env_bool, env_int, env_list, env_str, load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# 加载 .env 文件（如果存在）
load_dotenv(BASE_DIR / '.env')


# ==================== 基础配置 ====================

SECRET_KEY = env_str('SECRET_KEY', 'django-insecure-dev-key-change-me-in-production')

DEBUG = env_bool('DEBUG', True)

# 允许访问的域名/IP，多个用逗号分隔。生产环境务必指定具体域名
ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', ['*'] if DEBUG else [])

# CSRF 信任来源（HTTPS 部署时必填），如 https://shop.example.com
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', [])


# ==================== 应用配置 ====================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'shop',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
if not DEBUG:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'shop.context_processors.site_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# ==================== 数据库配置 ====================
# DB_ENGINE 支持 postgresql / sqlite
# 远程数据库只需修改 .env 中的 DB_HOST / DB_PORT 等参数，代码无需改动

DB_ENGINE = env_str('DB_ENGINE', 'sqlite').lower()

if DB_ENGINE in ('postgresql', 'postgres', 'psql'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env_str('DB_NAME', 'she_shop'),
            'USER': env_str('DB_USER', 'postgres'),
            'PASSWORD': env_str('DB_PASSWORD', ''),
            'HOST': env_str('DB_HOST', 'localhost'),
            'PORT': env_str('DB_PORT', '5432'),
            # 连接复用时间（秒），远程数据库建议设置以减少握手开销
            'CONN_MAX_AGE': env_int('DB_CONN_MAX_AGE', 60),
            'OPTIONS': {
                # 云数据库通常要求 SSL，可选 disable/allow/prefer/require/verify-ca/verify-full
                'sslmode': env_str('DB_SSLMODE', 'prefer'),
                'connect_timeout': env_int('DB_CONNECT_TIMEOUT', 10),
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / env_str('SQLITE_NAME', 'db.sqlite3'),
        }
    }


# ==================== 认证配置 ====================

AUTH_USER_MODEL = 'accounts.User'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': env_int('PASSWORD_MIN_LENGTH', 6)}},
] if env_bool('ENABLE_PASSWORD_VALIDATION', False) else []

# 会话有效期（秒），默认 2 周
SESSION_COOKIE_AGE = env_int('SESSION_COOKIE_AGE', 60 * 60 * 24 * 14)


# ==================== 国际化 ====================

LANGUAGE_CODE = env_str('LANGUAGE_CODE', 'zh-hans')
TIME_ZONE = env_str('TIME_ZONE', 'Asia/Shanghai')
USE_I18N = True
USE_TZ = True


# ==================== 静态文件与媒体文件 ====================

STATIC_URL = env_str('STATIC_URL', '/static/')
STATIC_ROOT = BASE_DIR / env_str('STATIC_ROOT', 'staticfiles')
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

MEDIA_URL = env_str('MEDIA_URL', '/media/')
MEDIA_ROOT = Path(env_str('MEDIA_ROOT', str(BASE_DIR / 'media')))

# 生产环境用 WhiteNoise 压缩静态文件
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'
        if not DEBUG else 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

# 生产环境是否由 Django 提供媒体文件服务
# 已配置 Nginx 或对象存储时保持 False，性能更好
SERVE_MEDIA = env_bool('SERVE_MEDIA', False)

# 上传文件大小限制（字节），默认 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = env_int('MAX_UPLOAD_SIZE', 10 * 1024 * 1024)
FILE_UPLOAD_MAX_MEMORY_SIZE = DATA_UPLOAD_MAX_MEMORY_SIZE

# 单次最多上传图片数
MAX_UPLOAD_IMAGES = env_int('MAX_UPLOAD_IMAGES', 9)

# 单个商品最多生成的规格组合数
# 组合数 = 各规格维度取值数的乘积，设置上限避免维度过多时数据膨胀
MAX_SKU_COMBINATIONS = env_int('MAX_SKU_COMBINATIONS', 200)

# 商品最多可定义的规格维度数（如颜色、尺码、型号）
MAX_SPEC_DIMENSIONS = env_int('MAX_SPEC_DIMENSIONS', 5)


# ==================== 站点配置 ====================

SITE_NAME = env_str('SITE_NAME', 'SheShop')
SITE_SLOGAN = env_str('SITE_SLOGAN', '专为女性打造的精品购物平台')
SITE_FOOTER_TEXT = env_str('SITE_FOOTER_TEXT', '让每一位女性都能找到属于自己的美丽')

# 前端资源加载方式：cdn（在线）/ local（离线）
FRONTEND_ASSETS = env_str('FRONTEND_ASSETS', 'cdn').lower()


# ==================== 安全配置（生产环境）====================

if not DEBUG:
    # 生产环境常见配置疏漏的提前预警，避免部署后出现难以定位的 400/500
    _warnings = []

    if not ALLOWED_HOSTS:
        _warnings.append(
            'ALLOWED_HOSTS 为空，所有请求都会返回 400。'
            '请在 .env 中设置，例如 ALLOWED_HOSTS=your-domain.com,1.2.3.4'
        )

    if SECRET_KEY.startswith(('django-insecure', 'dev-local')):
        _warnings.append(
            'SECRET_KEY 仍是开发用默认值，请在 .env 中更换为随机值。'
            '生成命令: python -c "import secrets; print(secrets.token_urlsafe(50))"'
        )

    if _warnings:
        import sys
        print('\n[配置警告]', file=sys.stderr)
        for _w in _warnings:
            print(f'  - {_w}', file=sys.stderr)
        print('', file=sys.stderr)

    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'SAMEORIGIN'

    # HTTPS 相关，仅在确认已配置 HTTPS 后开启
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', False)
    SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', False)
    CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', False)

    # 反向代理（Nginx）转发 HTTPS 时需要
    if env_bool('USE_X_FORWARDED_PROTO', False):
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# ==================== 日志配置 ====================

LOG_LEVEL = env_str('LOG_LEVEL', 'INFO' if not DEBUG else 'DEBUG')
LOG_DIR = BASE_DIR / 'logs'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
}

# 生产环境额外写文件日志
if env_bool('LOG_TO_FILE', False):
    LOG_DIR.mkdir(exist_ok=True)
    LOGGING['handlers']['file'] = {
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': str(LOG_DIR / 'app.log'),
        'maxBytes': env_int('LOG_MAX_BYTES', 10 * 1024 * 1024),
        'backupCount': env_int('LOG_BACKUP_COUNT', 5),
        'formatter': 'verbose',
        'encoding': 'utf-8',
    }
    LOGGING['root']['handlers'].append('file')


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
