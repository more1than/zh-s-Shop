import base64
import pickle

from django_redis import get_redis_connection


def merge_cart_cookie_to_redis(request, user, response):
    """
    登录时合并购物车
    :param request: 登录时借用的请求对象
    :param user: 登录时借用的用户对象
    :param response: 登录时借用的响应对象
    :return:

    # cookie 数据格式
    {
        "sku_id_1": {"count": 1, "selected": True},
        "sku_id_2": {"count": 1, "selected": True},
    }
    """
    # 获取cookie并校验
    cart_str = request.COOKIES.get("cart")
    # 把cookie中的字符串转换为字典
    if cart_str is None:
        return
    cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
    # 创建redis连接对象
    redis_conn = get_redis_connection("cart")
    pl = redis_conn.pipeline()
    # 遍历cookie购物车大字典，把sku_id及count向redis的hash中存储
    for sku_id in cart_dict:
        pl.hset("cart_%d" % user.id, sku_id, cart_dict[sku_id]["count"])
        # 如果cookie中商品勾选
        if cart_dict[sku_id]["selected"]:
            pl.sadd("selected_%d" % user.id, sku_id)
    pl.execute()
    # 清空cookie
    response.delete_cookie("cart")  # 删除cookie
    return True
