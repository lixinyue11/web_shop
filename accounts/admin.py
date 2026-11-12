from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'user_type', 'shop_name', 'is_active', 'date_joined']
    list_filter = ['user_type', 'is_active']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('用户类型', {'fields': ('user_type', 'phone')}),
        ('店铺信息', {'fields': ('shop_name', 'shop_logo', 'shop_desc')}),
    )
