"""
Excel数据服务层
- 一级目录：data/categories/ 下的文件夹
- 二级目录：每个Excel文件的工作簿(Sheet)
- 商品数据：工作簿中的行数据，图片嵌入Excel
"""
import os
import uuid
import base64
from pathlib import Path
from datetime import datetime
from io import BytesIO
from django.conf import settings

try:
    import openpyxl
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

try:
    from PIL import Image as PILImage
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def ensure_dirs():
    """确保数据目录存在"""
    dirs = [
        settings.DATA_DIR,
        settings.CATEGORIES_DIR,
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def get_categories():
    """获取所有一级类目(文件夹)"""
    ensure_dirs()
    categories = []
    if settings.CATEGORIES_DIR.exists():
        for item in sorted(settings.CATEGORIES_DIR.iterdir()):
            if item.is_dir():
                categories.append({
                    'id': item.name,
                    'name': item.name,
                    'path': str(item),
                    'subcategories': get_subcategories(item.name)
                })
    return categories


def get_subcategories(category_id):
    """获取二级类目(Excel文件中的工作簿)"""
    cat_path = settings.CATEGORIES_DIR / category_id
    subcategories = []
    if cat_path.exists():
        for xlsx_file in sorted(cat_path.glob('*.xlsx')):
            if HAS_OPENPYXL:
                try:
                    wb = openpyxl.load_workbook(xlsx_file, read_only=True)
                    for sheet_name in wb.sheetnames:
                        subcategories.append({
                            'id': f"{xlsx_file.stem}_{sheet_name}",
                            'name': sheet_name,
                            'file': xlsx_file.name,
                            'category': category_id
                        })
                    wb.close()
                except Exception:
                    pass
    return subcategories


def create_category(name):
    """创建一级类目"""
    ensure_dirs()
    cat_path = settings.CATEGORIES_DIR / name
    if not cat_path.exists():
        cat_path.mkdir(parents=True)
        return True
    return False


def delete_category(name):
    """删除一级类目"""
    import shutil
    cat_path = settings.CATEGORIES_DIR / name
    if cat_path.exists() and cat_path.is_dir():
        shutil.rmtree(cat_path)
        return True
    return False


def create_subcategory(category_id, subcategory_name, file_name=None):
    """创建二级类目(在Excel中创建新工作簿)"""
    if not HAS_OPENPYXL:
        return False

    cat_path = settings.CATEGORIES_DIR / category_id
    if not cat_path.exists():
        cat_path.mkdir(parents=True)

    if not file_name:
        file_name = f"{category_id}_products.xlsx"

    xlsx_path = cat_path / file_name

    if xlsx_path.exists():
        wb = openpyxl.load_workbook(xlsx_path)
    else:
        wb = openpyxl.Workbook()
        # 删除默认的Sheet
        if 'Sheet' in wb.sheetnames:
            del wb['Sheet']

    if subcategory_name not in wb.sheetnames:
        ws = wb.create_sheet(subcategory_name)
        # 设置表头
        headers = ['ID', '商品名称', '价格', '原价', '库存', '描述', '是否上架', '是否推荐', '创建时间', '图片数量']
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)
        wb.save(xlsx_path)
        wb.close()
        return True

    wb.close()
    return False


def delete_subcategory(category_id, subcategory_name, file_name):
    """删除二级类目"""
    if not HAS_OPENPYXL:
        return False

    xlsx_path = settings.CATEGORIES_DIR / category_id / file_name
    if xlsx_path.exists():
        wb = openpyxl.load_workbook(xlsx_path)
        if subcategory_name in wb.sheetnames:
            del wb[subcategory_name]
            if len(wb.sheetnames) == 0:
                wb.close()
                os.remove(xlsx_path)
            else:
                wb.save(xlsx_path)
                wb.close()
            return True
        wb.close()
    return False


def get_products(category_id=None, subcategory_name=None, file_name=None):
    """获取商品列表"""
    if not HAS_OPENPYXL:
        return []

    products = []

    if category_id and subcategory_name and file_name:
        # 获取特定二级类目的商品
        xlsx_path = settings.CATEGORIES_DIR / category_id / file_name
        if xlsx_path.exists():
            products.extend(_read_products_from_sheet(xlsx_path, subcategory_name, category_id))
    elif category_id:
        # 获取一级类目下所有商品
        cat_path = settings.CATEGORIES_DIR / category_id
        if cat_path.exists():
            for xlsx_file in cat_path.glob('*.xlsx'):
                wb = openpyxl.load_workbook(xlsx_file, read_only=True)
                for sheet_name in wb.sheetnames:
                    products.extend(_read_products_from_sheet(xlsx_file, sheet_name, category_id))
                wb.close()
    else:
        # 获取所有商品
        for cat_dir in settings.CATEGORIES_DIR.iterdir():
            if cat_dir.is_dir():
                for xlsx_file in cat_dir.glob('*.xlsx'):
                    wb = openpyxl.load_workbook(xlsx_file, read_only=True)
                    for sheet_name in wb.sheetnames:
                        products.extend(_read_products_from_sheet(xlsx_file, sheet_name, cat_dir.name))
                    wb.close()

    return products


def _read_products_from_sheet(xlsx_path, sheet_name, category_id):
    """从工作簿读取商品"""
    products = []
    try:
        wb = openpyxl.load_workbook(xlsx_path)
        if sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            for row in range(2, ws.max_row + 1):
                product_id = ws.cell(row=row, column=1).value
                if product_id:
                    products.append({
                        'id': str(product_id),
                        'name': ws.cell(row=row, column=2).value or '',
                        'price': float(ws.cell(row=row, column=3).value or 0),
                        'original_price': float(ws.cell(row=row, column=4).value or 0) if ws.cell(row=row, column=4).value else None,
                        'stock': int(ws.cell(row=row, column=5).value or 0),
                        'description': ws.cell(row=row, column=6).value or '',
                        'is_active': ws.cell(row=row, column=7).value == '是',
                        'is_featured': ws.cell(row=row, column=8).value == '是',
                        'created_at': ws.cell(row=row, column=9).value or '',
                        'image_count': int(ws.cell(row=row, column=10).value or 0),
                        'category': category_id,
                        'subcategory': sheet_name,
                        'file': xlsx_path.name,
                        'row': row
                    })
        wb.close()
    except Exception as e:
        print(f"Error reading products: {e}")
    return products


def get_product(product_id):
    """获取单个商品详情"""
    all_products = get_products()
    for p in all_products:
        if p['id'] == product_id:
            return p
    return None


def save_product(category_id, subcategory_name, file_name, product_data, images=None):
    """保存商品(新增或更新)"""
    if not HAS_OPENPYXL:
        return None

    xlsx_path = settings.CATEGORIES_DIR / category_id / file_name
    if not xlsx_path.exists():
        create_subcategory(category_id, subcategory_name, file_name)

    wb = openpyxl.load_workbook(xlsx_path)
    if subcategory_name not in wb.sheetnames:
        ws = wb.create_sheet(subcategory_name)
        headers = ['ID', '商品名称', '价格', '原价', '库存', '描述', '是否上架', '是否推荐', '创建时间', '图片数量']
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)
    else:
        ws = wb[subcategory_name]

    product_id = product_data.get('id')
    row = None

    if product_id:
        # 查找现有行
        for r in range(2, ws.max_row + 1):
            if str(ws.cell(row=r, column=1).value) == str(product_id):
                row = r
                break

    if not row:
        # 新增
        row = ws.max_row + 1
        product_id = str(uuid.uuid4())[:8]

    # 写入数据
    ws.cell(row=row, column=1, value=product_id)
    ws.cell(row=row, column=2, value=product_data.get('name', ''))
    ws.cell(row=row, column=3, value=float(product_data.get('price', 0)))
    ws.cell(row=row, column=4, value=float(product_data.get('original_price', 0)) if product_data.get('original_price') else None)
    ws.cell(row=row, column=5, value=int(product_data.get('stock', 0)))
    ws.cell(row=row, column=6, value=product_data.get('description', ''))
    ws.cell(row=row, column=7, value='是' if product_data.get('is_active') else '否')
    ws.cell(row=row, column=8, value='是' if product_data.get('is_featured') else '否')
    ws.cell(row=row, column=9, value=product_data.get('created_at') or datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    # 处理图片
    image_count = 0
    if images and HAS_PIL:
        # 图片存储到单独的sheet
        img_sheet_name = f"_img_{product_id}"
        if img_sheet_name in wb.sheetnames:
            del wb[img_sheet_name]
        img_ws = wb.create_sheet(img_sheet_name)

        for idx, img_file in enumerate(images):
            try:
                img = PILImage.open(img_file)
                img.thumbnail((300, 300))
                img_io = BytesIO()
                img.save(img_io, format='PNG')
                img_io.seek(0)

                xl_img = XLImage(img_io)
                cell = f"A{idx + 1}"
                img_ws.add_image(xl_img, cell)
                image_count += 1
            except Exception as e:
                print(f"Error saving image: {e}")

    ws.cell(row=row, column=10, value=image_count)
    wb.save(xlsx_path)
    wb.close()

    return product_id


def delete_product(category_id, subcategory_name, file_name, product_id):
    """删除商品"""
    if not HAS_OPENPYXL:
        return False

    xlsx_path = settings.CATEGORIES_DIR / category_id / file_name
    if not xlsx_path.exists():
        return False

    wb = openpyxl.load_workbook(xlsx_path)
    if subcategory_name not in wb.sheetnames:
        wb.close()
        return False

    ws = wb[subcategory_name]
    for row in range(2, ws.max_row + 1):
        if str(ws.cell(row=row, column=1).value) == str(product_id):
            ws.delete_rows(row)
            # 删除图片sheet
            img_sheet_name = f"_img_{product_id}"
            if img_sheet_name in wb.sheetnames:
                del wb[img_sheet_name]
            wb.save(xlsx_path)
            wb.close()
            return True

    wb.close()
    return False


def get_product_images(category_id, file_name, product_id):
    """获取商品图片(Base64编码)"""
    if not HAS_OPENPYXL:
        return []

    xlsx_path = settings.CATEGORIES_DIR / category_id / file_name
    if not xlsx_path.exists():
        return []

    images = []
    try:
        wb = openpyxl.load_workbook(xlsx_path)
        img_sheet_name = f"_img_{product_id}"
        if img_sheet_name in wb.sheetnames:
            ws = wb[img_sheet_name]
            for img in ws._images:
                img_data = img._data()
                b64 = base64.b64encode(img_data).decode('utf-8')
                images.append(f"data:image/png;base64,{b64}")
        wb.close()
    except Exception as e:
        print(f"Error getting images: {e}")

    return images


# ============ 用户数据管理 ============

def get_users():
    """获取所有用户"""
    if not HAS_OPENPYXL:
        return []

    ensure_dirs()
    users = []

    if settings.USERS_FILE.exists():
        wb = openpyxl.load_workbook(settings.USERS_FILE)
        ws = wb.active
        for row in range(2, ws.max_row + 1):
            username = ws.cell(row=row, column=1).value
            if username:
                users.append({
                    'username': username,
                    'password': ws.cell(row=row, column=2).value or '',
                    'user_type': ws.cell(row=row, column=3).value or 'customer',
                    'created_at': ws.cell(row=row, column=4).value or '',
                })
        wb.close()

    return users


def get_user(username):
    """获取单个用户"""
    users = get_users()
    for u in users:
        if u['username'] == username:
            return u
    return None


def create_user(username, password, user_type='customer'):
    """创建用户"""
    if not HAS_OPENPYXL:
        return False

    ensure_dirs()

    if get_user(username):
        return False  # 用户已存在

    if settings.USERS_FILE.exists():
        wb = openpyxl.load_workbook(settings.USERS_FILE)
        ws = wb.active
    else:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "用户"
        headers = ['用户名', '密码', '用户类型', '注册时间']
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)

    row = ws.max_row + 1
    ws.cell(row=row, column=1, value=username)
    ws.cell(row=row, column=2, value=password)
    ws.cell(row=row, column=3, value=user_type)
    ws.cell(row=row, column=4, value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    wb.save(settings.USERS_FILE)
    wb.close()
    return True


# ============ 收藏数据管理 ============

def get_favorites(username=None):
    """获取收藏列表"""
    if not HAS_OPENPYXL:
        return []

    ensure_dirs()
    favorites = []

    if settings.FAVORITES_FILE.exists():
        wb = openpyxl.load_workbook(settings.FAVORITES_FILE)
        ws = wb.active
        for row in range(2, ws.max_row + 1):
            user = ws.cell(row=row, column=1).value
            if user and (username is None or user == username):
                favorites.append({
                    'id': ws.cell(row=row, column=2).value,
                    'username': user,
                    'product_id': ws.cell(row=row, column=3).value,
                    'product_name': ws.cell(row=row, column=4).value,
                    'created_at': ws.cell(row=row, column=5).value,
                })
        wb.close()

    return favorites


def add_favorite(username, product_id, product_name):
    """添加收藏"""
    if not HAS_OPENPYXL:
        return False

    ensure_dirs()

    # 检查是否已收藏
    favorites = get_favorites(username)
    for f in favorites:
        if f['product_id'] == product_id:
            return False

    if settings.FAVORITES_FILE.exists():
        wb = openpyxl.load_workbook(settings.FAVORITES_FILE)
        ws = wb.active
    else:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "收藏"
        headers = ['用户名', 'ID', '商品ID', '商品名称', '收藏时间']
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)

    row = ws.max_row + 1
    ws.cell(row=row, column=1, value=username)
    ws.cell(row=row, column=2, value=str(uuid.uuid4())[:8])
    ws.cell(row=row, column=3, value=product_id)
    ws.cell(row=row, column=4, value=product_name)
    ws.cell(row=row, column=5, value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    wb.save(settings.FAVORITES_FILE)
    wb.close()
    return True


def remove_favorite(username, product_id):
    """取消收藏"""
    if not HAS_OPENPYXL:
        return False

    if not settings.FAVORITES_FILE.exists():
        return False

    wb = openpyxl.load_workbook(settings.FAVORITES_FILE)
    ws = wb.active

    for row in range(2, ws.max_row + 1):
        if ws.cell(row=row, column=1).value == username and ws.cell(row=row, column=3).value == product_id:
            ws.delete_rows(row)
            wb.save(settings.FAVORITES_FILE)
            wb.close()
            return True

    wb.close()
    return False


# ============ 订单数据管理 ============

def get_orders(username=None):
    """获取订单列表"""
    if not HAS_OPENPYXL:
        return []

    ensure_dirs()
    orders = []

    if settings.ORDERS_FILE.exists():
        wb = openpyxl.load_workbook(settings.ORDERS_FILE)
        ws = wb.active
        for row in range(2, ws.max_row + 1):
            user = ws.cell(row=row, column=1).value
            if user and (username is None or user == username):
                orders.append({
                    'order_no': ws.cell(row=row, column=2).value,
                    'username': user,
                    'product_id': ws.cell(row=row, column=3).value,
                    'product_name': ws.cell(row=row, column=4).value,
                    'price': float(ws.cell(row=row, column=5).value or 0),
                    'quantity': int(ws.cell(row=row, column=6).value or 1),
                    'total': float(ws.cell(row=row, column=7).value or 0),
                    'status': ws.cell(row=row, column=8).value or '待处理',
                    'contact_name': ws.cell(row=row, column=9).value or '',
                    'contact_phone': ws.cell(row=row, column=10).value or '',
                    'address': ws.cell(row=row, column=11).value or '',
                    'note': ws.cell(row=row, column=12).value or '',
                    'created_at': ws.cell(row=row, column=13).value or '',
                })
        wb.close()

    return orders


def create_order(username, product_id, product_name, price, quantity, contact_name, contact_phone, address, note=''):
    """创建订单"""
    if not HAS_OPENPYXL:
        return None

    ensure_dirs()

    if settings.ORDERS_FILE.exists():
        wb = openpyxl.load_workbook(settings.ORDERS_FILE)
        ws = wb.active
    else:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "订单"
        headers = ['用户名', '订单号', '商品ID', '商品名称', '单价', '数量', '总价', '状态', '联系人', '联系电话', '地址', '备注', '下单时间']
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)

    order_no = datetime.now().strftime('%Y%m%d%H%M%S') + str(uuid.uuid4())[:4].upper()
    total = price * quantity

    row = ws.max_row + 1
    ws.cell(row=row, column=1, value=username)
    ws.cell(row=row, column=2, value=order_no)
    ws.cell(row=row, column=3, value=product_id)
    ws.cell(row=row, column=4, value=product_name)
    ws.cell(row=row, column=5, value=price)
    ws.cell(row=row, column=6, value=quantity)
    ws.cell(row=row, column=7, value=total)
    ws.cell(row=row, column=8, value='待处理')
    ws.cell(row=row, column=9, value=contact_name)
    ws.cell(row=row, column=10, value=contact_phone)
    ws.cell(row=row, column=11, value=address)
    ws.cell(row=row, column=12, value=note)
    ws.cell(row=row, column=13, value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    wb.save(settings.ORDERS_FILE)
    wb.close()
    return order_no


def update_order_status(order_no, status):
    """更新订单状态"""
    if not HAS_OPENPYXL:
        return False

    if not settings.ORDERS_FILE.exists():
        return False

    wb = openpyxl.load_workbook(settings.ORDERS_FILE)
    ws = wb.active

    for row in range(2, ws.max_row + 1):
        if ws.cell(row=row, column=2).value == order_no:
            ws.cell(row=row, column=8, value=status)
            wb.save(settings.ORDERS_FILE)
            wb.close()
            return True

    wb.close()
    return False
