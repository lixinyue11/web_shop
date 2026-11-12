"""
环境变量工具

支持从 .env 文件加载配置，并提供类型转换辅助函数。
优先级：系统环境变量 > .env 文件 > 代码默认值
（这样服务器上用 docker/systemd 注入的变量不会被 .env 覆盖）
"""
import os
from pathlib import Path


def load_dotenv(path):
    """
    加载 .env 文件到 os.environ。

    格式说明：
        KEY=value          # 基本格式
        KEY="value"        # 支持引号包裹
        # 注释行           # 以 # 开头的行会被忽略
        KEY=               # 空值

    已存在的系统环境变量不会被覆盖。
    """
    path = Path(path)
    if not path.exists():
        return False

    with open(path, 'r', encoding='utf-8') as f:
        for raw_line in f:
            line = raw_line.strip()

            # 跳过空行和注释
            if not line or line.startswith('#'):
                continue

            if '=' not in line:
                continue

            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip()

            # 去掉包裹的引号
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]

            # 系统环境变量优先，不覆盖
            if key and key not in os.environ:
                os.environ[key] = value

    return True


def env_str(key, default=''):
    """读取字符串环境变量"""
    value = os.environ.get(key)
    if value is None or value == '':
        return default
    return value


def env_bool(key, default=False):
    """
    读取布尔环境变量。
    以下值视为 True：1, true, yes, on, y（不区分大小写）
    """
    value = os.environ.get(key)
    if value is None or value == '':
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on', 'y')


def env_int(key, default=0):
    """读取整数环境变量，解析失败时返回默认值"""
    value = os.environ.get(key)
    if value is None or value == '':
        return default
    try:
        return int(value.strip())
    except (TypeError, ValueError):
        return default


def env_list(key, default=None, separator=','):
    """
    读取列表环境变量，按分隔符切分并去除空白项。
    例：ALLOWED_HOSTS=example.com,www.example.com
    """
    if default is None:
        default = []

    value = os.environ.get(key)
    if value is None or value.strip() == '':
        return default

    return [item.strip() for item in value.split(separator) if item.strip()]
