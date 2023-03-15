from celery_tasks.main import celery_app
from django.template import loader
from django.conf import settings
import os

from goods.models import SKU
from goods.utils import get_categories


@celery_app.task(name="generate_static_list_search_html")
def generate_static_list_search_html():
    """
    生成静态的商品列表页和搜索结果页html文件
    """
    # 商品分类菜单
    categories = get_categories()

    # 渲染模板，生成静态html文件
    context = {
        "categories": categories,
    }

    template = loader.get_template("list.html")
    html_text = template.render(context)
    file_path = os.path.join(settings.GENERATED_STATIC_HTML_FILES_DIR, "list.html")
    with open(file_path, "w") as f:
        f.write(html_text)


@celery_app.task(name="generate_static_sku_detail_html")
def generate_static_sku_detail_html(sku_id):
    """
    生成静态的商品详情页面
    :param sku_id: 商品sku id
    """
    # 商品分类菜单
    categories = get_categories()

    # 获取当前sku信息
    sku = SKU.objects.get(id=sku_id)
    sku.images = sku.skuimage_set.all()

    # 面包屑导航信息中的频道
    goods = sku.goods
    goods.channel = goods.category1.goodschannel_set.all()[0]

    # 渲染模板，生成静态html文件
    context = {
        "categories": categories,
        "goods": goods,
        "sku": sku,
    }

    template = loader.get_template("detail.html")
    html_text = template.render(context)
    file_path = os.path.join(settings.GENERATED_STATIC_HTML_FILES_DIR, "goods/{}.html".format(str(sku_id)))
    with open(file_path, "w") as f:
        f.write(html_text)
