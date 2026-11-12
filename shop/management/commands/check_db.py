"""
数据库连接检查命令

用法：
    python manage.py check_db

用于部署前验证数据库配置是否正确，会显示当前连接的数据库信息
（密码会被隐藏），并尝试建立实际连接。
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = '检查数据库连接配置是否正确'

    def handle(self, *args, **options):
        db = settings.DATABASES['default']
        engine = db['ENGINE'].split('.')[-1]

        self.stdout.write(self.style.MIGRATE_HEADING('\n当前数据库配置:'))
        self.stdout.write(f"  类型:     {engine}")

        if 'sqlite' in engine:
            self.stdout.write(f"  文件:     {db['NAME']}")
            exists = str(db['NAME']) and __import__('pathlib').Path(db['NAME']).exists()
            self.stdout.write(f"  文件存在: {'是' if exists else '否（首次迁移后自动创建）'}")
        else:
            self.stdout.write(f"  主机:     {db.get('HOST')}:{db.get('PORT')}")
            self.stdout.write(f"  数据库:   {db.get('NAME')}")
            self.stdout.write(f"  用户:     {db.get('USER')}")
            self.stdout.write(f"  密码:     {'已设置' if db.get('PASSWORD') else self.style.WARNING('未设置')}")
            self.stdout.write(f"  SSL模式:  {db.get('OPTIONS', {}).get('sslmode', '-')}")
            self.stdout.write(f"  连接复用: {db.get('CONN_MAX_AGE', 0)} 秒")

        self.stdout.write(self.style.MIGRATE_HEADING('\n正在测试连接...'))

        try:
            conn = connections['default']
            conn.ensure_connection()

            with conn.cursor() as cursor:
                if 'postgresql' in engine:
                    cursor.execute('SELECT version()')
                    version = cursor.fetchone()[0]
                    self.stdout.write(f"  服务端版本: {version.split(',')[0]}")
                else:
                    cursor.execute('SELECT sqlite_version()')
                    self.stdout.write(f"  SQLite 版本: {cursor.fetchone()[0]}")

            self.stdout.write(self.style.SUCCESS('\n连接成功\n'))

        except OperationalError as exc:
            self.stdout.write(self.style.ERROR(f'\n连接失败: {exc}\n'))
            self.stdout.write('排查建议:')
            if 'postgresql' in engine:
                self.stdout.write('  1. 确认 PostgreSQL 服务已启动')
                self.stdout.write('  2. 检查 .env 中 DB_HOST / DB_PORT / DB_USER / DB_PASSWORD 是否正确')
                self.stdout.write('  3. 确认数据库已创建: CREATE DATABASE she_shop;')
                self.stdout.write('  4. 远程数据库需检查防火墙和 pg_hba.conf 是否允许当前 IP')
            else:
                self.stdout.write('  1. 检查项目目录是否有写入权限')
            self.stdout.write('')
            raise SystemExit(1)
