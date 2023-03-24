from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView
from drf_haystack.viewsets import HaystackViewSet
from goods.models import SKU
from goods.serializers import SKUSerializer, SKUSearchSerializer


class SKUListView(ListAPIView):
    """ 商品列表数据查询 """
    serializer_class = SKUSerializer

    # queryset = SKU.objects.filter()
    filter_backends = [OrderingFilter]  # 指定过滤后端为排序过滤
    ordering_fields = ["create_time", "price", "sales"]  # 指定排序字段

    def get_queryset(self):
        """ 如果当前视图中没有定义get / post方法，就没法定义一个参数用来接收正则组提取出来的url路径参数
            可以利用试图对象的args / kwargs属性去获取
            起了别名用kwargs获取，没有起别名用args获取
        """
        category_id = self.kwargs.get("category_id")
        return SKU.objects.filter(is_launched=True, category_id=category_id)


class SKUSearchViewSet(HaystackViewSet):
    """SKU搜索"""
    index_models = [SKU]  # 指定查询集

    serializer_class = SKUSearchSerializer  # 指定序列化器
