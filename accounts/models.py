"""用户模型"""
from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """自定义用户"""
    USER_TYPE_CHOICES = (
        ('customer', '顾客'),
        ('merchant', '商家'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='customer', verbose_name='用户类型')
    phone = models.CharField(max_length=20, blank=True, verbose_name='手机号')
    # 商家信息
    shop_name = models.CharField(max_length=100, blank=True, verbose_name='店铺名称')
    shop_logo = models.ImageField(upload_to='shops/', blank=True, null=True, verbose_name='店铺Logo')
    shop_desc = models.TextField(blank=True, verbose_name='店铺简介')

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return self.shop_name if self.is_merchant and self.shop_name else self.username

    @property
    def is_merchant(self):
        return self.user_type == 'merchant'

    @property
    def display_name(self):
        return self.shop_name if self.is_merchant and self.shop_name else self.username
