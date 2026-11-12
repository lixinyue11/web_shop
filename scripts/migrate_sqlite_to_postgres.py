"""
SQLite 数据迁移到 PostgreSQL

把现有 SQLite 中的数据完整搬到 PostgreSQL，适用于本地开发转生产部署。

使用步骤：
    1. 确保 .env 中 DB_ENGINE=sqlite（即当前数据所在库）
    2. 运行导出：
         python scripts/migrate_sqlite_to_postgres.py export
    3. 修改 .env 中 DB_ENGINE=postgresql 并填好连接参数
    4. 建表并导入：
         python manage.py migrate
         python scripts/migrate_sqlite_to_postgres.py import

注意：
    - 媒体文件（media 目录）需另行复制到新服务器
    - 导入前目标数据库应为空库，避免主键冲突
"""
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DUMP_FILE = BASE_DIR / 'data_dump.json'

# 这些表由 Django 自动管理，导出时排除以避免导入冲突
EXCLUDED = [
    'contenttypes',
    'auth.permission',
    'admin.logentry',
    'sessions.session',
]


def run_django(args):
    """调用 manage.py 子命令"""
    cmd = [sys.executable, str(BASE_DIR / 'manage.py')] + args
    return subprocess.run(cmd, cwd=str(BASE_DIR))


def current_engine():
    """读取 .env 中当前配置的数据库类型"""
    sys.path.insert(0, str(BASE_DIR))
    from config.env_utils import env_str, load_dotenv
    load_dotenv(BASE_DIR / '.env')
    return env_str('DB_ENGINE', 'sqlite').lower()


def do_export():
    engine = current_engine()
    if engine not in ('sqlite', 'sqlite3'):
        print(f'当前 DB_ENGINE={engine}，导出前请先改回 sqlite')
        return 1

    print('正在从 SQLite 导出数据...')

    args = ['dumpdata', '--natural-foreign', '--natural-primary',
            '--indent', '2', '--output', str(DUMP_FILE)]
    for item in EXCLUDED:
        args += ['--exclude', item]

    result = run_django(args)
    if result.returncode != 0:
        print('导出失败')
        return result.returncode

    size_kb = DUMP_FILE.stat().st_size / 1024
    print(f'\n导出完成: {DUMP_FILE}  ({size_kb:.1f} KB)')
    print('\n下一步:')
    print('  1. 修改 .env: DB_ENGINE=postgresql，并填写连接参数')
    print('  2. python manage.py check_db      # 验证连接')
    print('  3. python manage.py migrate       # 在新库建表')
    print('  4. python scripts/migrate_sqlite_to_postgres.py import')
    return 0


def do_import():
    if not DUMP_FILE.exists():
        print(f'未找到导出文件: {DUMP_FILE}')
        print('请先运行: python scripts/migrate_sqlite_to_postgres.py export')
        return 1

    engine = current_engine()
    if engine not in ('postgresql', 'postgres', 'psql'):
        print(f'当前 DB_ENGINE={engine}，导入前请先改为 postgresql')
        return 1

    print('正在导入数据到 PostgreSQL...')
    result = run_django(['loaddata', str(DUMP_FILE)])

    if result.returncode == 0:
        print('\n导入完成')
        print('\n后续事项:')
        print('  - 把 media 目录复制到新服务器')
        print('  - 确认数据无误后可删除 data_dump.json')
    else:
        print('\n导入失败。常见原因:')
        print('  - 目标库非空导致主键冲突，可先执行 python manage.py flush')
        print('  - 迁移文件未同步，确认已运行 python manage.py migrate')

    return result.returncode


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('export', 'import'):
        print(__doc__)
        return 1

    return do_export() if sys.argv[1] == 'export' else do_import()


if __name__ == '__main__':
    sys.exit(main())
