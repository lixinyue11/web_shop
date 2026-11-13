"""商店视图"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import OperationalError, transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from functools import wraps
from .models import (
    Category, SubCategory, Product, ProductImage, ProductSKU,
    Favorite, Order, ImageCollection,
)
from .forms import OrderForm, ProductForm, SKUValuesForm
from .services import build_spec_combinations, parse_spec_inputs, resolve_order_sku, sync_product_skus, validate_spec_inputs
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
    products = (Product.objects.filter(merchant=merchant, is_active=True)
                .prefetch_related('images', 'specs', 'skus'))

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
    product = get_object_or_404(Product, id=product_id, is_active=True)
    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=request.user, product=product).exists()

    related = (Product.objects.filter(merchant=product.merchant, is_active=True)
               .exclude(id=product_id).prefetch_related('images', 'specs', 'skus')[:4])

    return render(request, 'shop/product_detail.html', {
        'product': product,
        'is_favorited': is_favorited,
        'related_products': related,
        'specs': list(product.specs.all()),
        'sku_data': {
            sku.spec_values: {'id': str(sku.pk), 'price': str(sku.price), 'stock': sku.stock}
            for sku in product.skus.all() if sku.is_active
        },
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
    favorites = Favorite.objects.filter(user=request.user).select_related('product', 'product__merchant').prefetch_related('product__specs', 'product__skus')
    return render(request, 'shop/my_favorites.html', {'favorites': favorites})


@login_required
def create_order(request, product_id):
    """创建订单并扣减对应规格的库存"""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    selected_sku_id = request.POST.get('sku_id', '') if request.method == 'POST' else request.GET.get('sku', '')
    form = OrderForm(request.POST if request.method == 'POST' else None, initial={'quantity': 1})

    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                product = get_object_or_404(Product.objects.select_for_update(), id=product_id, is_active=True)
                sku, unit_price, error = resolve_order_sku(product, selected_sku_id)
                if error:
                    raise ValidationError(error)

                quantity = form.cleaned_data['quantity']
                inventory = sku or product
                if quantity > inventory.stock:
                    raise ValidationError(f'库存不足，当前仅剩 {inventory.stock} 件')

                order = form.save(commit=False)
                order.user = request.user
                order.product = product
                order.product_name = product.name
                order.product_price = unit_price
                order.sku = sku
                if sku:
                    order.spec_text = ProductSKU.SEPARATOR.join(
                        f'{spec.name}：{value}' for spec, value in zip(product.specs.all(), sku.value_list)
                    )
                order.total_amount = unit_price * quantity
                Order._meta.get_field('total_amount').clean(order.total_amount, order)
                inventory.stock -= quantity
                inventory.save(update_fields=['stock'])
                order.save()
        except ValidationError as exc:
            form.add_error(None, exc)
        except OperationalError as exc:
            if 'locked' not in str(exc).lower():
                raise
            form.add_error(None, '库存正在更新，请重新提交订单')
        else:
            messages.success(request, f'下单成功！订单号：{order.order_no}')
            return redirect('my_orders')

    skus = list(product.skus.filter(is_active=True))
    selected_sku = next((sku for sku in skus if str(sku.pk) == selected_sku_id and sku.is_available), None)
    if selected_sku or not product.has_specs:
        form.fields['quantity'].widget.attrs['max'] = selected_sku.stock if selected_sku else product.stock
    return render(request, 'shop/create_order.html', {
        'product': product,
        'form': form,
        'skus': skus,
        'selected_sku': selected_sku,
    })


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
    products = (Product.objects.filter(merchant=request.user)
                .select_related('category', 'subcategory')
                .prefetch_related('images', 'specs', 'skus'))
    return render(request, 'merchant/products.html', {
        'products': products,
    })


@merchant_required
def merchant_product_add(request):
    """添加商品"""
    return merchant_product_form(request, Product(merchant=request.user))


@merchant_required
def merchant_product_edit(request, product_id):
    """编辑自己的商品"""
    if request.method == 'POST':
        with transaction.atomic():
            product = get_object_or_404(Product.objects.select_for_update(), id=product_id, merchant=request.user)
            return merchant_product_form(request, product)

    product = get_object_or_404(Product, id=product_id, merchant=request.user)
    return merchant_product_form(request, product)


def merchant_product_form(request, product):
    is_edit = product.pk is not None
    form = ProductForm(request.POST if request.method == 'POST' else None, instance=product)
    existing_specs = list(product.specs.all()) if is_edit else []
    specs = existing_specs

    if request.method == 'POST':
        specs = parse_spec_inputs(request.POST)
        form.is_valid()
        try:
            combinations = validate_spec_inputs(specs)
        except ValidationError as exc:
            form.add_error(None, exc)

        if not form.errors:
            with transaction.atomic():
                product = form.save()
                existing_names = [spec.name for spec in existing_specs]
                names = [spec.name for spec in specs]
                product.specs.exclude(name__in=names).delete()
                for order, spec in enumerate(specs):
                    product.specs.update_or_create(name=spec.name, defaults={'values': spec.values, 'sort_order': order})

                # 维度发生变化时，原有组合中的取值可能已不再对应原来的规格。
                created, removed = sync_product_skus(product, combinations, reset=names != existing_names)

                images = limit_images(request.FILES.getlist('images'))
                if images:
                    product.images.all().delete()
                    for i, img in enumerate(images):
                        ProductImage.objects.create(product=product, image=img, is_main=(i == 0))

            messages.success(request, '商品已更新' if is_edit else '商品添加成功')
            if specs and (created or removed):
                messages.info(request, f'新增 {created} 个规格组合，移除 {removed} 个。请设置组合的价格和库存。')
                return redirect('merchant_product_skus', product_id=product.id)
            return redirect('merchant_products')

    return render(request, 'merchant/product_form.html', {
        'form': form,
        'product': product,
        'is_edit': is_edit,
        'specs': specs,
    })


@merchant_required
def merchant_product_skus(request, product_id):
    """设置各组合的价格、库存和可售状态"""
    products = Product.objects.filter(merchant=request.user)
    if request.method == 'POST':
        with transaction.atomic():
            product = get_object_or_404(products.select_for_update(), id=product_id)
            try:
                save_sku_settings(request, product)
            except ValidationError as exc:
                for error in exc.messages:
                    messages.error(request, error)
        return redirect('merchant_product_skus', product_id=product_id)

    product = get_object_or_404(products, id=product_id)
    return render(request, 'merchant/product_skus.html', {
        'product': product,
        'specs': list(product.specs.all()),
        'skus': list(product.skus.all()),
    })


def save_sku_settings(request, product):
    action = request.POST.get('action', 'save')
    if action == 'regenerate':
        combinations = build_spec_combinations(product.specs.all())
        created, removed = sync_product_skus(product, combinations)
        messages.success(request, f'已重新生成，新增 {created} 个、移除 {removed} 个')
        return

    if action == 'batch':
        form = SKUValuesForm({
            'price': request.POST.get('batch_price', ''),
            'stock': request.POST.get('batch_stock', ''),
        })
        for field in form.fields.values():
            field.required = False
        if not form.is_valid():
            raise ValidationError(['批量设置：' + error for errors in form.errors.values() for error in errors])
        updates = {key: value for key, value in form.cleaned_data.items() if value is not None}
        if updates:
            product.skus.all().update(**updates)
            messages.success(request, '批量设置完成')
        return

    if action != 'save':
        raise ValidationError('未知的规格管理操作')

    updates = []
    for sku in product.skus.all():
        price = request.POST.get(f'price_{sku.pk}')
        stock = request.POST.get(f'stock_{sku.pk}')
        if price is None or stock is None:
            raise ValidationError('规格组合已更新，请重新填写')
        current_stock = sku.stock
        form = SKUValuesForm({'price': price, 'stock': stock}, instance=sku)
        if not form.is_valid():
            raise ValidationError([f'「{sku.spec_values}」：{error}' for errors in form.errors.values() for error in errors])
        sku = form.save(commit=False)
        # 仅修改价格或可售状态时，保留页面加载后发生的库存扣减。
        if stock == request.POST.get(f'original_stock_{sku.pk}'):
            sku.stock = current_stock
        sku.is_active = request.POST.get(f'active_{sku.pk}') == 'on'
        updates.append(sku)

    if updates:
        ProductSKU.objects.bulk_update(updates, ['price', 'stock', 'is_active'])
    messages.success(request, '规格设置已保存')


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

    orders = Order.objects.filter(product__merchant=request.user).select_related('user', 'product', 'sku')
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
