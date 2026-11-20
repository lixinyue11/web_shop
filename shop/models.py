"""商品相关模型"""
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.conf import settings
import uuid
from datetime import datetime


class Category(models.Model):
    """一级类目"""
    name = models.CharField(max_length=100, unique=True, verbose_name=_('类目名称'))
    icon = models.CharField(max_length=50, blank=True, default='bi-tag', verbose_name=_('图标'))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_('排序'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('创建时间'))

    class Meta:
        verbose_name = _('一级类目')
        verbose_name_plural = _('一级类目')
        ordering = ['sort_order', '-created_at']

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    """二级类目"""
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories', verbose_name=_('所属一级类目'))
    name = models.CharField(max_length=100, verbose_name=_('类目名称'))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_('排序'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('创建时间'))

    class Meta:
        verbose_name = _('二级类目')
        verbose_name_plural = _('二级类目')
        ordering = ['sort_order', '-created_at']
        unique_together = ['category', 'name']

    def __str__(self):
        return f"{self.category.name} / {self.name}"


class ThirdCategory(models.Model):
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='third_categories')
    name = models.CharField(max_length=100, verbose_name=_('类目名称'))

    class Meta:
        ordering = ['name', 'pk']
        unique_together = [('subcategory', 'name')]

    def __str__(self):
        return self.name


class Product(models.Model):
    """商品"""
    merchant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='products', verbose_name=_('商家'))
    name = models.CharField(max_length=200, verbose_name=_('商品名称'))
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name=_('一级类目'))
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='products', verbose_name=_('二级类目'))
    third_category = models.ForeignKey(ThirdCategory, on_delete=models.SET_NULL, related_name='products', blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('价格'))
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_('原价'))
    stock = models.PositiveIntegerField(default=0, verbose_name=_('库存'))
    description = models.TextField(blank=True, verbose_name=_('商品描述'))
    is_active = models.BooleanField(default=True, verbose_name=_('上架'))
    is_featured = models.BooleanField(default=False, verbose_name=_('推荐'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('创建时间'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('更新时间'))

    class Meta:
        verbose_name = _('商品')
        verbose_name_plural = _('商品')
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def main_image(self):
        return self.images.first()

    @property
    def has_specs(self):
        """是否配置了规格（颜色/尺码等）"""
        return self.specs.exists()

    @property
    def available_skus(self):
        """可售的规格组合"""
        return self.skus.filter(is_active=True, stock__gt=0)

    @property
    def display_price(self):
        """
        展示价格：优先取有库存的规格最低价，售罄时取上架规格最低价。
        用于列表页和详情页的起步价显示。
        """
        if self.has_specs:
            active = [sku for sku in self.skus.all() if sku.is_active]
            prices = [sku.price for sku in active if sku.stock] or [sku.price for sku in active]
            return min(prices, default=self.price)
        return self.price

    @property
    def total_stock(self):
        """总库存：有规格时为各组合库存之和"""
        if self.has_specs:
            return sum(sku.stock for sku in self.skus.all() if sku.is_active)
        return self.stock


class ProductImage(models.Model):
    """商品图片"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', verbose_name=_('商品'))
    image = models.ImageField(upload_to='products/%Y%m/', verbose_name=_('图片'))
    is_main = models.BooleanField(default=False, verbose_name=_('主图'))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_('排序'))

    class Meta:
        verbose_name = _('商品图片')
        verbose_name_plural = _('商品图片')
        ordering = ['-is_main', 'sort_order']


class ProductSpec(models.Model):
    """
    规格维度

    每个商品可自由定义若干维度，如「颜色」「尺码」「型号」，
    也可自定义「材质」「风格」等。选项值以逗号分隔存储。
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='specs', verbose_name=_('商品'))
    name = models.CharField(max_length=50, verbose_name=_('规格名称'))
    values = models.CharField(max_length=500, verbose_name=_('可选值'), help_text=_('多个值用逗号分隔，如：红色,黑色,白色'))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_('排序'))

    class Meta:
        verbose_name = _('规格维度')
        verbose_name_plural = _('规格维度')
        ordering = ['sort_order', 'id']
        unique_together = ['product', 'name']

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    @property
    def value_list(self):
        """拆分为列表，兼容中英文逗号并去重去空"""
        raw = self.values.replace('，', ',')
        seen, result = set(), []
        for item in raw.split(','):
            item = item.strip()
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result


class ProductSKU(models.Model):
    """
    规格组合（SKU）

    由各规格维度的取值组合而成，每个组合有独立的价格和库存。
    spec_values 按规格维度的排序拼接，如「红色 / M / 标准版」。
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='skus', verbose_name=_('商品'))
    spec_values = models.CharField(max_length=300, verbose_name=_('规格组合'))
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('价格'))
    stock = models.PositiveIntegerField(default=0, verbose_name=_('库存'))
    is_active = models.BooleanField(default=True, verbose_name=_('可售'))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_('排序'))

    SEPARATOR = ' / '

    class Meta:
        verbose_name = _('规格组合')
        verbose_name_plural = _('规格组合')
        ordering = ['sort_order', 'id']
        unique_together = ['product', 'spec_values']

    def __str__(self):
        return f"{self.product.name} [{self.spec_values}]"

    @property
    def value_list(self):
        """拆回各维度的取值，顺序与 product.specs 一致"""
        return [v.strip() for v in self.spec_values.split(self.SEPARATOR)]

    @property
    def is_available(self):
        return self.is_active and self.stock > 0


class Favorite(models.Model):
    """收藏"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites', verbose_name=_('用户'))
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorited_by', verbose_name=_('商品'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('收藏时间'))

    class Meta:
        verbose_name = _('收藏')
        verbose_name_plural = _('收藏')
        unique_together = ['user', 'product']
        ordering = ['-created_at']


class Order(models.Model):
    """订单"""
    STATUS_CHOICES = (
        ('pending', _('待处理')),
        ('confirmed', _('已确认')),
        ('shipped', _('已发货')),
        ('completed', _('已完成')),
        ('cancelled', _('已取消')),
    )
    order_no = models.CharField(max_length=32, unique=True, verbose_name=_('订单号'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders', verbose_name=_('用户'))
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, verbose_name=_('商品'))
    product_name = models.CharField(max_length=200, verbose_name=_('商品名称'))
    product_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('商品单价'))
    # 规格信息：sku 可能被商家删除，spec_text 冗余保存下单时的规格文本
    sku = models.ForeignKey('ProductSKU', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('规格组合'))
    spec_text = models.TextField(blank=True, verbose_name=_('所选规格'))
    quantity = models.PositiveIntegerField(default=1, verbose_name=_('数量'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('总金额'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name=_('状态'))
    contact_name = models.CharField(max_length=50, verbose_name=_('联系人'))
    contact_phone = models.CharField(max_length=20, verbose_name=_('联系电话'))
    address = models.TextField(verbose_name=_('收货地址'))
    note = models.TextField(blank=True, verbose_name=_('备注'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('下单时间'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('更新时间'))

    class Meta:
        verbose_name = _('订单')
        verbose_name_plural = _('订单')
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_no:
            self.order_no = datetime.now().strftime('%Y%m%d%H%M%S') + uuid.uuid4().hex[:6].upper()
        super().save(*args, **kwargs)


class ImageCollection(models.Model):
    """用户图片收集"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_images', verbose_name=_('上传用户'))
    merchant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='collected_images', verbose_name=_('接收商家'))
    image = models.ImageField(upload_to='collections/%Y%m/', verbose_name=_('图片'))
    note = models.TextField(blank=True, verbose_name=_('备注说明'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('上传时间'))

    class Meta:
        verbose_name = _('图片收集')
        verbose_name_plural = _('图片收集')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} -> {self.merchant.display_name}"
