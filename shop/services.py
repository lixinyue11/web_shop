"""业务逻辑辅助函数"""
from itertools import product as cartesian_product
from math import prod

from django.conf import settings
from django.core.exceptions import ValidationError

from .models import ProductSpec, ProductSKU


def build_spec_combinations(specs):
    """
    根据规格维度生成所有取值组合（笛卡尔积）。

    返回按维度顺序拼接的组合，例如 ['红色 / M', '红色 / L']。

    任一维度没有有效取值时返回空列表。
    """
    value_lists = [spec.value_list for spec in specs]

    if value_lists and prod(map(len, value_lists)) > settings.MAX_SKU_COMBINATIONS:
        raise ValidationError(f'规格组合不能超过 {settings.MAX_SKU_COMBINATIONS} 个，请减少选项')

    combinations = [ProductSKU.SEPARATOR.join(combo) for combo in cartesian_product(*value_lists)] if value_lists else []
    if any(len(combo) > 300 for combo in combinations):
        raise ValidationError('规格组合文字太长，请缩短规格选项')
    return combinations


def sync_product_skus(product, combinations, *, reset=False):
    """
    按商品当前的规格维度同步 SKU 组合。

    已存在的组合保留其价格和库存，新增组合继承商品默认价格，
    规格变更后不再成立的组合会被删除。

    返回 (新增数, 删除数)。调用方在商品事务内保存规格和组合。
    """
    existing = {sku.spec_values: sku for sku in product.skus.all()}
    obsolete = set(existing) if reset else set(existing) - set(combinations)
    if obsolete:
        product.skus.filter(spec_values__in=obsolete).delete()

    to_create = []
    to_reorder = []
    for order, spec_values in enumerate(combinations):
        sku = existing.get(spec_values)
        if not sku or spec_values in obsolete:
            to_create.append(ProductSKU(
                product=product,
                spec_values=spec_values,
                price=product.price,
                sort_order=order,
            ))
        elif sku.sort_order != order:
            sku.sort_order = order
            to_reorder.append(sku)

    if to_create:
        ProductSKU.objects.bulk_create(to_create)
    if to_reorder:
        ProductSKU.objects.bulk_update(to_reorder, ['sort_order'])

    return len(to_create), len(obsolete)


def parse_spec_inputs(post_data):
    """
    从商品表单的 POST 数据中解析规格维度。

    表单字段形如 spec_name_0 / spec_values_0、spec_name_1 / spec_values_1。
    忽略整行为空的输入，保留其余行供验证和重新展示。
    """
    specs = []
    for key in post_data:
        prefix, _, index = key.rpartition('_')
        if prefix in ('spec_name', 'spec_values') and index.isascii() and index.isdecimal():
            specs.append(index)

    rows = []
    for index in sorted(set(specs), key=lambda index: (len(index), index)):
        name = post_data.get(f'spec_name_{index}', '').strip()
        values = post_data.get(f'spec_values_{index}', '').strip()
        if name or values:
            rows.append(ProductSpec(name=name, values=values))
    return rows


def validate_spec_inputs(specs):
    if len(specs) > settings.MAX_SPEC_DIMENSIONS:
        raise ValidationError(f'最多可填写 {settings.MAX_SPEC_DIMENSIONS} 个规格维度')

    names = set()
    for spec in specs:
        if not spec.name or len(spec.name) > 50:
            raise ValidationError('规格名称须填写，且最多 50 个字符')
        values = spec.value_list
        if not values:
            raise ValidationError(f'请填写「{spec.name}」的规格选项')
        if spec.name in names:
            raise ValidationError(f'规格名称「{spec.name}」重复')
        if any(ProductSKU.SEPARATOR in f' {value} ' for value in values):
            raise ValidationError(f'「{spec.name}」的选项中，请去掉斜线两侧的空格，例如使用 USB/Type-C')
        spec.values = ','.join(values)
        if len(spec.values) > 500:
            raise ValidationError(f'「{spec.name}」的选项合计不能超过 500 个字符')
        names.add(spec.name)

    return build_spec_combinations(specs)


def resolve_order_sku(product, sku_id):
    """
    下单时校验并取出 SKU。

    返回 (sku, 单价, 错误信息)。无规格商品返回 (None, 商品价格, None)。
    """
    if not product.has_specs:
        if sku_id:
            return None, None, '商品规格已更新，请重新确认订单'
        if product.stock <= 0:
            return None, product.price, '该商品已售罄'
        return None, product.price, None

    if not sku_id:
        return None, None, '请选择商品规格'

    if not (sku_id.isascii() and sku_id.isdecimal() and len(sku_id) <= 19 and int(sku_id) <= 9223372036854775807):
        return None, None, '所选规格不存在，请重新选择'

    sku = product.skus.filter(id=sku_id).first()
    if not sku:
        return None, None, '所选规格不存在，请重新选择'

    if not sku.is_active:
        return None, None, f'规格「{sku.spec_values}」已下架'

    if sku.stock <= 0:
        return None, None, f'规格「{sku.spec_values}」已售罄'

    return sku, sku.price, None
