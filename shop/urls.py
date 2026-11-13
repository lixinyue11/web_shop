from django.urls import path
from . import views

urlpatterns = [
    # 前台
    path('', views.home, name='home'),
    path('shop/<int:merchant_id>/', views.shop_detail, name='shop_detail'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('favorite/<int:product_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('my/favorites/', views.my_favorites, name='my_favorites'),
    path('order/create/<int:product_id>/', views.create_order, name='create_order'),
    path('my/orders/', views.my_orders, name='my_orders'),

    # 图片收集
    path('shop/<int:merchant_id>/upload/', views.upload_image_to_merchant, name='upload_image'),
    path('my/uploads/', views.my_uploaded_images, name='my_uploaded_images'),

    # 商家后台
    path('merchant/', views.merchant_dashboard, name='merchant_dashboard'),
    path('merchant/shop/', views.merchant_shop_settings, name='merchant_shop_settings'),
    path('merchant/categories/', views.merchant_categories, name='merchant_categories'),
    path('merchant/products/', views.merchant_products, name='merchant_products'),
    path('merchant/product/add/', views.merchant_product_add, name='merchant_product_add'),
    path('merchant/product/edit/<int:product_id>/', views.merchant_product_edit, name='merchant_product_edit'),
    path('merchant/product/<int:product_id>/skus/', views.merchant_product_skus, name='merchant_product_skus'),
    path('merchant/product/delete/<int:product_id>/', views.merchant_product_delete, name='merchant_product_delete'),
    path('merchant/orders/', views.merchant_orders, name='merchant_orders'),
    path('merchant/favorites/', views.merchant_favorites, name='merchant_favorites'),
    path('merchant/collections/', views.merchant_image_collections, name='merchant_image_collections'),
    path('merchant/collection/delete/<int:collection_id>/', views.merchant_delete_collection, name='merchant_delete_collection'),

    # API
    path('api/subcategories/<int:category_id>/', views.get_subcategories_api, name='get_subcategories'),
]
