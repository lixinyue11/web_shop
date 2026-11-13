"""模板全局上下文 - 把站点配置注入所有模板"""
from django.conf import settings


def site_settings(request):
    """
    使模板中可以直接使用 {{ SITE_NAME }}、{{ FRONTEND_ASSETS }} 等变量，
    避免站点名称、资源加载方式等硬编码在模板里。
    """
    return {
        'SITE_NAME': settings.SITE_NAME,
        'SITE_SLOGAN': settings.SITE_SLOGAN,
        'SITE_FOOTER_TEXT': settings.SITE_FOOTER_TEXT,
        'FRONTEND_ASSETS': settings.FRONTEND_ASSETS,
        'MAX_UPLOAD_IMAGES': settings.MAX_UPLOAD_IMAGES,
        'MAX_SPEC_DIMENSIONS': settings.MAX_SPEC_DIMENSIONS,
        'MAX_SKU_COMBINATIONS': settings.MAX_SKU_COMBINATIONS,
    }
