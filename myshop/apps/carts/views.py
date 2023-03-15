import base64
import pickle

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from carts.serializers import CartSerializer, SKUCartSerializer, CartDeletedSerializer, CartSelectedAllSerializer
from django_redis import get_redis_connection

# Create your views here.
from goods.models import SKU


class CartView(APIView):
    """购物车增删改查"""

    def perform_authentication(self, request):
        """重写此方法直接pass，可以延后认证，延后到第一次通过request.user或request.auth才去认证"""
        pass

    def post(self, request):
        # 创建序列化器进行反序列化
        serializer = CartSerializer(data=request.data)
        # 调用is_valid进行校验
        serializer.is_valid(raise_exception=True)
        # 获取校验后的数据
        sku_id = serializer.validated_data.get("sku_id")
        count = serializer.validated_data.get("count")
        selected = serializer.validated_data.get("selected")

        try:
            user = request.user  # 执行此行代码会触发认证逻辑，如果用户未登录会触发异常
        except:
            user = None
        response = Response(serializer.data, status=status.HTTP_201_CREATED)
        # 判断用户是否通过认证，主要鉴别是否是匿名用户
        if user and user.is_authenticated:
            """登录用户操作redis购物车数据
            hash: {"sku_id_1": 2, "sku_id_2": 1}
            set: {sku_id_1}
            商品信息和数量存储在hash中, 是否勾选存储在set集合中
            """
            # 创建redis连接对象
            redis_conn = get_redis_connection("cart")
            pl = redis_conn.pipeline()  # 创建管道

            # 添加：如果添加的sku_id在hash中已经存在，做增量,不存在则创建
            pl.hincrby("cart_%d" % user.id, sku_id, count)

            # 把勾选的商品sku_id存储到set集合中
            if selected:  # 判断当前商品是否勾选
                pl.sadd("selected_%d" % user.id, sku_id)
            pl.execute()

        else:
            """未登录用户操作cookie购物车数据
            {
                "sku_id_1": {"count": 1, "selected": True}, 
                "sku_id_2": {"count": 1, "selected": True}, 
            }
            """
            # 获取cookie购物车数据
            cart_str = request.COOKIE.get("cart")
            if cart_str:  # 说明cookie购物车中已经有商品
                # 把字符串转换为byte类型的字符串
                cart_str_bytes = cart_str.encode()
                # 把byte类型的字符串转换成bytes类型
                cart_bytes = base64.b64decode(cart_str_bytes)
                # 把bytes类型转换为python字典
                cart_dict = pickle.loads(cart_bytes)
            else:  # 说明是第一次添加
                cart_dict = {}
            # 增量计算
            if sku_id in cart_dict:
                # 判断当前要添加的sku_id在字典中是否已经存在
                origin_count = cart_dict[sku_id]["count"]
                # 原购买数据和本次购买数据累加
                count += origin_count

            # 把新的商品添加到cart_dict字典中
            cart_dict[sku_id] = {
                "count": count,
                "selected": selected,
            }
            # 先将字典转换成bytes类型
            cart_bytes = pickle.dumps(cart_dict)
            # 再将bytes类型转换成bytes类型的字符串
            cart_str_bytes = base64.b64encode(cart_bytes)
            # 把bytes类型字符转转换成字符串
            cart_str = cart_str_bytes.decode()

            # 设置cookie
            response.set_cookie("cart", cart_str)

        return response

    def get(self, request):
        try:
            user = request.user
        except:
            user = None
        if user and user.is_authenticated:
            """登录用户获取redis购物车数据"""
            # 创建redis连接对象
            redis_conn = get_redis_connection("cart")
            # 获取hash数据 {sku_id_1: 1, sku_id_2: 1}
            cart_redis_dict = redis_conn.hgetall("cat_%d" % user.id)
            # 获取set集合数据 {sku_id_1}
            selected = redis_conn.semebers("selected_%d" % user.id)
            # 将redis购物车数据格式转换成和cookie购物车数据格式一致
            cart_dict = {}
            for sku_id_bytes in cart_redis_dict:
                cart_dict[int(sku_id_bytes)] = {
                    "count": int(cart_redis_dict[sku_id_bytes]),
                    "selected": sku_id_bytes in selected
                }
        else:
            """未登录用户获取cookie购物车数据
            {
                "sku_id_1": {"count": 1, "selected": True}, 
                "sku_id_2": {"count": 1, "selected": True}, 
            }
            """
            cart_str = request.COOKIES.get("cart")
            if cart_str:
                # 把字符串转换为byte类型的字符串
                cart_str_bytes = cart_str.encode()
                # 把byte类型的字符串转换成bytes类型
                cart_bytes = base64.b64decode(cart_str_bytes)
                # 把bytes类型转换为python字典
                cart_dict = pickle.loads(cart_bytes)
            else:
                return Response({"message": "没有购物车数据"}, status=status.HTTP_400_BAD_REQUEST)
        # 根据sku_id查询sku模型
        sku_ids = cart_dict.keys()
        # 直接查询出所有的sku模型返回查询集
        skus = SKU.objects.filter(id__in=sku_ids)
        # 给每个sku模型多定义一个count和selected属性
        for sku in skus:
            sku.count = cart_dict[sku.id]["count"]
            sku.selected = cart_dict[sku.id]["selected"]
        # 创建序列化器进行序列化
        serializer = SKUCartSerializer(skus, many=True)

        # 响应
        return Response(serializer.data)

    def put(self, request):
        # 创建序列化器
        serializer = CartSerializer(data=request.data)
        # 校验
        serializer.is_valid(raise_exception=True)
        # 获取校验后的数据
        sku_id = serializer.validated_data.get("sku_id")
        count = serializer.validated_data.get("count")
        selected = serializer.validated_data.get("selected")
        response = Response(serializer.data, status=status.HTTP_200_OK)
        try:
            user = request.user
        except:
            user = None
        if user and user.is_authenticated:
            """登录用户修改redis购物车数据"""
            redis_conn = get_redis_connection("cart")
            pl = redis_conn.pipeline()
            # 覆盖sku_id 对应的count
            pl.hset("cart_%d" % user.id, sku_id, count)

            if selected:
                pl.sadd("selected_%d" % user.id, sku_id)
            else:
                pl.srem("selected_%d" % user.id, sku_id)
            pl.execute()

        else:
            """未登录用户修改cookie购物车数据"""
            cart_str = request.COOKIES.get("cart")
            if cart_str:
                # 把字符串转换为byte类型的字符串
                cart_str_bytes = cart_str.encode()
                # 把byte类型的字符串转换成bytes类型
                cart_bytes = base64.b64decode(cart_str_bytes)
                # 把bytes类型转换为python字典
                cart_dict = pickle.loads(cart_bytes)
            else:
                return Response({"message": "未获取cookie"}, status=status.HTTP_400_BAD_REQUEST)

            # 直接覆盖原cookie
            cart_dict[sku_id] = {
                "count": count,
                "selected": selected
            }
            # response = Response(serializer.data)
            response.set_cookie("cart", base64.b64encode(pickle.dumps(cart_dict)).decode())
        return response

    def delete(self, request):
        serializer = CartDeletedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sku_id = serializer.validated_data.get("sku_id")
        response = Response(status=status.HTTP_204_NO_CONTENT)
        try:
            user = request.user
        except:
            user = None
        if user and user.is_authenticated:
            """登录用户删除redis购物车数据"""
            redis_conn = get_redis_connection("cart")
            pl = redis_conn.pipeline()
            pl.hdel("cart_%d" % user.id, sku_id)
            pl.srem("selected_%d" % user.id, sku_id)
            pl.execute()

        else:
            """未登录用户删除cookie购物车数据"""
            # 获取cookie
            cart_str = request.COOKIES.get("cart")
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                return Response({"message": "未获取到cookie"}, status=status.HTTP_400_BAD_REQUEST)
            if sku_id in cart_dict:
                del cart_dict[sku_id]

            if len(cart_dict.keys()):
                cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()
                response.set_cookie("cart", cart_str)

            else:  # cookie购物车数据已经清空了
                response.delete_cookie("cart")

        return response


class CartSelectedAllView(APIView):
    """购物车全选操作"""

    def perform_authentication(self, request):
        """重写此方法直接pass，可以延后认证，延后到第一次通过request.user或request.auth才去认证"""
        pass

    def put(self, request):
        """购物车全选"""
        serializer = CartSelectedAllSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        selected = serializer.validated_data.get("selected")
        response = Response(serializer.data)
        try:
            user = request.user
        except:
            user = None
        if user and user.is_authenticated:
            """登录用户操作redis数据"""
            redis_conn = get_redis_connection("cart")
            cart_redis_dict = redis_conn.hgetall("cart_%d" % user.id)
            sku_ids = cart_redis_dict.keys()
            if selected:  # 如果selected为true代表全选
                redis_conn.sadd("selected_%d" % user.id, *sku_ids)
            else:
                redis_conn.srem("selected_%d" % user.id, *sku_ids)
        else:
            """未登录用户操作cookie数据"""
            # 获取cookie数据
            cart_str = request.COOKIS.get("cart")
            # 校验
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                return Response({"message": "cookie 没有获取到"}, status=status.HTTP_400_BAD_REQUEST)
            for sku_id in cart_dict:
                cart_dict[sku_id]["selected"] = selected
            cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()
            request.set_cookie("cart", cart_str)
        return response
