"""商店视图"""
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from functools import wraps
from .models import Category, SubCategory, Product, ProductImage, Favorite, Order, ImageCollection
from accounts.models import User


def limit_images(images):
    """按配置的上限截断上传图片列表，上限见 .env 的 MAX_UPLOAD_IMAGES"""
    return images[:settings.MAX_UPLOAD_IMAGES]


def merchant_required(view_func):
    """商家验证装饰器"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, '请先登录')
            return redirect('login')
        if not request.user.is_merchant:
            messages.error(request, '需要商家权限')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


# ============ 前台页面 ============

def home(request):
    """首页 - 显示商家列表"""
    merchants = User.objects.filter(user_type='merchant')
    return render(request, 'shop/home.html', {
        'merchants': merchants,
    })


def shop_detail(request, merchant_id):
    """商家店铺页面"""
    merchant = get_object_or_404(User, id=merchant_id, user_type='merchant')
    categories = Category.objects.filter(products__merchant=merchant).distinct()
    products = Product.objects.filter(merchant=merchant, is_active=True)

    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)

    featured = products.filter(is_featured=True)[:4]

    return render(request, 'shop/shop_detail.html', {
        'merchant': merchant,
        'categories': categories,
        'products': products,
        'featured_products': featured,
        'current_category': int(category_id) if category_id else None,
    })


def product_detail(request, product_id):
    """商品详情"""
    product = get_object_or_404(Product, id=product_id)
    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=request.user, product=product).exists()

    # 同店铺其他商品推荐
    related = Product.objects.filter(merchant=product.merchant, is_active=True).exclude(id=product_id)[:4]

    return render(request, 'shop/product_detail.html', {
        'product': product,
        'is_favorited': is_favorited,
        'related_products': related,
    })


@login_required
def toggle_favorite(request, product_id):
    """收藏/取消收藏"""
    product = get_object_or_404(Product, id=product_id)
    fav, created = Favorite.objects.get_or_create(user=request.user, product=product)

    if not created:
        fav.delete()
        return JsonResponse({'success': True, 'favorited': False, 'message': '已取消收藏'})
    return JsonResponse({'success': True, 'favorited': True, 'message': '收藏成功'})


@login_required
def my_favorites(request):
    """我的收藏"""
    favorites = Favorite.objects.filter(user=request.user).select_related('product', 'product__merchant')
    return render(request, 'shop/my_favorites.html', {'favorites': favorites})


@login_required
def create_order(request, product_id):
    """创建订单"""
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        contact_name = request.POST.get('contact_name', '').strip()
        contact_phone = request.POST.get('contact_phone', '').strip()
        address = request.POST.get('address', '').strip()
        note = request.POST.get('note', '').strip()

        if not contact_name or not contact_phone or not address:
            messages.error(request, '请填写完整的收货信息')
        else:
            order = Order.objects.create(
                user=request.user,
                product=product,
                product_name=product.name,
                product_price=product.price,
                quantity=quantity,
                total_amount=product.price * quantity,
                contact_name=contact_name,
                contact_phone=contact_phone,
                address=address,
                note=note
            )
            messages.success(request, f'下单成功！订单号：{order.order_no}')
            return redirect('my_orders')

    return render(request, 'shop/create_order.html', {'product': product})


@login_required
def my_orders(request):
    """我的订单"""
    orders = Order.objects.filter(user=request.user).select_related('product', 'product__merchant')
    return render(request, 'shop/my_orders.html', {'orders': orders})


# ============ 商家后台 ============

@merchant_required
def merchant_dashboard(request):
    """商家后台首页"""
    products = Product.objects.filter(merchant=request.user)
    orders = Order.objects.filter(product__merchant=request.user)
    favorites = Favorite.objects.filter(product__merchant=request.user)
    collections = ImageCollection.objects.filter(merchant=request.user)

    return render(request, 'merchant/dashboard.html', {
        'product_count': products.count(),
        'order_count': orders.count(),
        'favorite_count': favorites.count(),
        'collection_count': collections.count(),
    })


@merchant_required
def merchant_shop_settings(request):
    """店铺设置"""
    if request.method == 'POST':
        request.user.shop_name = request.POST.get('shop_name', '').strip()
        request.user.shop_desc = request.POST.get('shop_desc', '').strip()
        if request.FILES.get('shop_logo'):
            request.user.shop_logo = request.FILES['shop_logo']
        request.user.save()
        messages.success(request, '店铺信息已更新')
        return redirect('merchant_shop_settings')

    return render(request, 'merchant/shop_settings.html')


@merchant_required
def merchant_categories(request):
    """类目管理"""
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_category':
            name = request.POST.get('name', '').strip()
            if name:
                Category.objects.get_or_create(name=name)
                messages.success(request, f'类目 "{name}" 创建成功')

        elif action == 'delete_category':
            cat_id = request.POST.get('category_id')
            Category.objects.filter(id=cat_id).delete()
            messages.success(request, '类目已删除')

        elif action == 'add_subcategory':
            cat_id = request.POST.get('category_id')
            subname = request.POST.get('subname', '').strip()
            if cat_id and subname:
                category = get_object_or_404(Category, id=cat_id)
                SubCategory.objects.get_or_create(category=category, name=subname)
                messages.success(request, f'二级类目 "{subname}" 创建成功')

        elif action == 'delete_subcategory':
            sub_id = request.POST.get('subcategory_id')
            SubCategory.objects.filter(id=sub_id).delete()
            messages.success(request, '二级类目已删除')

        return redirect('merchant_categories')

    categories = Category.objects.prefetch_related('subcategories').all()
    return render(request, 'merchant/categories.html', {'categories': categories})


@merchant_required
def merchant_products(request):
    """商品管理 - 只显示自己的商品"""
    products = Product.objects.filter(merchant=request.user).select_related('category', 'subcategory').prefetch_related('images')
    return render(request, 'merchant/products.html', {
        'products': products,
    })


@merchant_required
def merchant_product_add(request):
    """添加商品"""
    categories = Category.objects.prefetch_related('subcategories').all()

    if request.method == 'POST':
        category_id = request.POST.get('category')
        subcategory_id = request.POST.get('subcategory')

        category = get_object_or_404(Category, id=category_id)
        subcategory = get_object_or_404(SubCategory, id=subcategory_id)

        product = Product.objects.create(
            merchant=request.user,  # 关联当前商家
            name=request.POST.get('name', '').strip(),
            category=category,
            subcategory=subcategory,
            price=request.POST.get('price', 0),
            original_price=request.POST.get('original_price') or None,
            stock=request.POST.get('stock', 0),
            description=request.POST.get('description', ''),
            is_active=request.POST.get('is_active') == 'on',
            is_featured=request.POST.get('is_featured') == 'on',
        )

        images = limit_images(request.FILES.getlist('images'))
        for i, img in enumerate(images):
            ProductImage.objects.create(product=product, image=img, is_main=(i == 0))

        messages.success(request, '商品添加成功')
        return redirect('merchant_products')

    return render(request, 'merchant/product_form.html', {
        'categories': categories,
        'is_edit': False,
    })


@merchant_required
def merchant_product_edit(request, product_id):
    """编辑商品 - 只能编辑自己的商品"""
    product = get_object_or_404(Product, id=product_id, merchant=request.user)
    categories = Category.objects.prefetch_related('subcategories').all()

    if request.method == 'POST':
        product.name = request.POST.get('name', '').strip()
        product.price = request.POST.get('price', 0)
        product.original_price = request.POST.get('original_price') or None
        product.stock = request.POST.get('stock', 0)
        product.description = request.POST.get('description', '')
        product.is_active = request.POST.get('is_active') == 'on'
        product.is_featured = request.POST.get('is_featured') == 'on'
        product.save()

        images = limit_images(request.FILES.getlist('images'))
        if images:
            product.images.all().delete()
            for i, img in enumerate(images):
                ProductImage.objects.create(product=product, image=img, is_main=(i == 0))

        messages.success(request, '商品更新成功')
        return redirect('merchant_products')

    return render(request, 'merchant/product_form.html', {
        'categories': categories,
        'product': product,
        'is_edit': True,
    })


@merchant_required
def merchant_product_delete(request, product_id):
    """删除商品 - 只能删除自己的商品"""
    Product.objects.filter(id=product_id, merchant=request.user).delete()
    messages.success(request, '商品已删除')
    return redirect('merchant_products')


@merchant_required
def merchant_orders(request):
    """订单管理 - 只显示自己店铺的订单"""
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        status = request.POST.get('status')
        Order.objects.filter(id=order_id, product__merchant=request.user).update(status=status)
        messages.success(request, '订单状态已更新')
        return redirect('merchant_orders')

    orders = Order.objects.filter(product__merchant=request.user).select_related('user', 'product')
    return render(request, 'merchant/orders.html', {'orders': orders})


@merchant_required
def merchant_favorites(request):
    """收藏管理 - 只显示自己商品的收藏"""
    favorites = Favorite.objects.filter(product__merchant=request.user).select_related('user', 'product')
    return render(request, 'merchant/favorites.html', {'favorites': favorites})


def get_subcategories_api(request, category_id):
    """获取二级类目API"""
    subcategories = SubCategory.objects.filter(category_id=category_id).values('id', 'name')
    return JsonResponse({'subcategories': list(subcategories)})


# ============ 图片收集功能 ============

@login_required
def upload_image_to_merchant(request, merchant_id):
    """用户给商家上传图片"""
    merchant = get_object_or_404(User, id=merchant_id, user_type='merchant')

    if request.method == 'POST':
        images = limit_images(request.FILES.getlist('images'))
        note = request.POST.get('note', '').strip()

        if not images:
            messages.error(request, '请选择要上传的图片')
        else:
            for img in images:
                ImageCollection.objects.create(
                    user=request.user,
                    merchant=merchant,
                    image=img,
                    note=note
                )
            messages.success(request, f'成功上传 {len(images)} 张图片给 {merchant.display_name}')
            return redirect('shop_detail', merchant_id=merchant_id)

    return render(request, 'shop/upload_image.html', {'merchant': merchant})


@login_required
def my_uploaded_images(request):
    """我上传的图片"""
    images = ImageCollection.objects.filter(user=request.user).select_related('merchant')
    return render(request, 'shop/my_uploaded_images.html', {'images': images})


@merchant_required
def merchant_image_collections(request):
    """商家查看收到的图片"""
    collections = ImageCollection.objects.filter(merchant=request.user).select_related('user')
    return render(request, 'merchant/image_collections.html', {'collections': collections})


@merchant_required
def merchant_delete_collection(request, collection_id):
    """商家删除收到的图片"""
    ImageCollection.objects.filter(id=collection_id, merchant=request.user).delete()
    messages.success(request, '图片已删除')
    return redirect('merchant_image_collections')
