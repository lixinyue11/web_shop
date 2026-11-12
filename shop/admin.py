from django.contrib import admin
from .models import Category, SubCategory, Product, ProductImage, Favorite, Order, ImageCollection


class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'sort_order', 'created_at']
    inlines = [SubCategoryInline]


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'merchant', 'category', 'subcategory', 'price', 'stock', 'is_active', 'is_featured']
    list_filter = ['merchant', 'category', 'is_active', 'is_featured']
    search_fields = ['name', 'merchant__username', 'merchant__shop_name']
    inlines = [ProductImageInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_no', 'user', 'product_name', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'product__merchant']
    search_fields = ['order_no', 'user__username']


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    list_filter = ['product__merchant']


@admin.register(ImageCollection)
class ImageCollectionAdmin(admin.ModelAdmin):
    list_display = ['user', 'merchant', 'created_at']
    list_filter = ['merchant']
    search_fields = ['user__username', 'merchant__username', 'merchant__shop_name']
