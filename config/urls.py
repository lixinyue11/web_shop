"""SheShop URL 配置"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('', include('shop.urls')),
]

# 媒体文件服务
# 开发环境由 Django 直接提供；生产环境建议交给 Nginx 或对象存储，
# 若未配置 Nginx，可设置 SERVE_MEDIA=True 临时由 Django 提供
if settings.DEBUG or getattr(settings, 'SERVE_MEDIA', False):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# 静态文件：生产环境由 WhiteNoise 中间件处理，此处仅开发环境需要
if settings.DEBUG and settings.STATICFILES_DIRS:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
