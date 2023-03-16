from django_redis import get_redis_connection
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from goods.models import SKU
from decimal import Decimal
from rest_framework.generics import CreateAPIView
from orders.serializers import OrderSettlementSerializer, CommitOrderSerializer


class OrderSettlementView(APIView):
    """ 去结算 """

    permission_classes = [IsAuthenticated]  # 指定权限必须是登录用户

    def get(self, request):
        redis_conn = get_redis_connection("cart")
        # 获取redis中的hash和set数据
        cart_dict_redis = redis_conn.hgetall("cart_%d" % request.user.id)
        selected_ids = redis_conn.smembers("selected_%d" % request.user.id)

        cart_dict = {}
        # 去除勾选的数据包装到新字典中 {已勾选商品id: 已勾选商品数量}
        for sku_id_bytes in selected_ids:
            cart_dict[int(sku_id_bytes)] = int(cart_dict_redis[sku_id_bytes])

        # 获取勾选商品SKU商品模型
        skus = SKU.objects.filter(id__in=cart_dict.keys())

        # 遍历SKUs查询集添加count
        for sku in skus:
            sku.count = cart_dict[sku.id]

        # 运费数据
        freight = Decimal("10.00")
        data_dict = {"freight": freight, "skus": skus}

        serializer = OrderSettlementSerializer(data_dict)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)


class CommitOrderView(CreateAPIView):
    """保存订单"""
    serializer_class = CommitOrderSerializer

    permission_classes = [IsAuthenticated]
