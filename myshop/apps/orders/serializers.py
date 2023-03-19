from datetime import datetime
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers
from django_redis import get_redis_connection
from goods.models import SKU
from orders.models import OrderInfo, OrderGoods


class CartSKUSerializer(serializers.ModelSerializer):
    """订单中的商品序列化器"""
    count = serializers.IntegerField(label="商品的购买数量")

    class Meta:
        model = SKU
        fields = ["id", "name", "default_image_url", "price", "count"]


class OrderSettlementSerializer(serializers.Serializer):
    """订单序列化器"""
    skus = CartSKUSerializer(many=True)
    freight = serializers.DecimalField(label="运费", max_digits=10, decimal_places=2)


class CommitOrderSerializer(serializers.ModelSerializer):
    """保存订单序列化器"""

    class Meta:
        model = OrderInfo
        fields = ["order_id", "address", "pay_method"]
        read_only_fields = ["order_id"]  # 只序列化输出，不做反序列化
        extra_kwargs = {
            "address": {"write_only": True},
            "pay_method": {"write_only": True},
        }

    def create(self, validated_data):
        # 获取订单需要的信息
        user = self.context['request'].user
        # %09d 若不足9位数用0补齐
        order_id = datetime.now().strftime("%Y%m%d%H%M%S") + "%09d" % user.id

        pay_method = validated_data.get("pay_method")
        # 订单状态
        status = OrderInfo.ORDER_STATUS_ENUM["UNPAID"] if pay_method == OrderInfo.PAY_METHODS_ENUM["ALIPAY"] else \
            OrderInfo.ORDER_STATUS_ENUM["UNSEND"]

        with transaction.atomic():  # 手动开启事务
            # 创建事务的回滚点
            save_point = transaction.savepoint()
            try:
                # 保存订单基本信息
                order_info = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=validated_data.get("address"),
                    total_count=0,  # 订单中商品的总数量
                    total_amount=Decimal("0.00"),  # 订单总金额
                    freight=Decimal("10.00"),
                    pay_method=pay_method,
                    status=status,
                )
                # 从redis读取勾选商品信息
                redis_conn = get_redis_connection("cart")
                cart_dict_redis = redis_conn.hgetall("cart_%d" % user.id)
                selected_ids = redis_conn.smembers("selected_%d" % user.id)
                for sku_id_bytes in selected_ids:
                    while True:  # 让用户对一个商品有无数次下单机会，直到库存真正不足为止
                        # 获取sku对象
                        sku = SKU.objects.get(id=sku_id_bytes)
                        # 获取当前商品购买数量
                        buy_count = int(cart_dict_redis[sku_id_bytes])
                        # 获取sku中模型的库存和销量
                        origin_sales = sku.sales  # 当前要购买商品的原有销量
                        origin_stock = sku.stock  # 当前要购买商品的原有库存
                        # 判断库存
                        if buy_count > origin_stock:
                            raise serializers.ValidationError("库存不足")

                        # 减少库存
                        # 计算新的库存和销量
                        new_sales = origin_sales + buy_count
                        new_stock = origin_stock + buy_count
                        # sku.sales = new_sales
                        # sku.stock = new_stock
                        # sku.save()

                        # update返回更新数据得条数
                        # 再次查询，如果能查询到库存再进行修改操作
                        result = SKU.objects.filter(stock=origin_stock, id=sku_id_bytes).update(stock=new_stock,
                                                                                                sales=new_sales)
                        if result == 0:  # 如果没有修改成功证明有抢夺同一商品问题
                            continue

                        # 修改spu销量
                        spu = sku.goods
                        spu.sales += new_sales
                        spu.save()

                        # 保存订单商品信息
                        OrderGoods.objects.create(
                            order=order_info,
                            sku=sku,
                            count=buy_count,
                            price=sku.price,
                        )
                        # 累加计算总数量和总价
                        order_info.total_count += buy_count
                        order_info.total_amount += (sku.price * buy_count)

                        break

                # 最后加入邮费和保存订单信息
                order_info.total_amount += order_info.freight
                order_info.save()
            except Exception:
                # 进行暴力回滚
                transaction.savepoint_rollback(save_point)
                raise serializers.ValidationError("库存不足")
            else:
                # 如果中间未出现问题，就提交事务
                transaction.savepoint_commit(save_point)

        # 清空购物车中已结算商品
        pl = redis_conn.pipeline()
        pl.hdel("cart_%d" % user.id, *selected_ids)
        pl.srem("selected_%d" % user.id, *selected_ids)
        pl.execute()

        # 返回订单模型对象
        return order_info
