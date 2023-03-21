from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from orders.models import OrderInfo
from alipay import AliPay
from django.conf import settings

from payment.models import Payment


class PaymentView(APIView):
    """生成支付宝链接"""
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        # 获取当前请求用户对象
        user = request.user
        # 校验订单有效性
        try:
            order_model = OrderInfo.objects.get(order_id=order_id, user=user, status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'])
        except OrderInfo.DoesNotExist:
            return Response({"msg": "订单有误"}, status=status.HTTP_400_BAD_REQUEST)
        # 创建alipay SDK中提供的支付对象
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            app_private_key_string="app_private_key_string",
            alipay_public_key_string="alipay_public_key_string",
            sign_type="RSA2",  # RSA 或 RSA2, 推荐RSA2更加安全
            debug=True,  # 默认False
        )
        # 调用SDK的方法获取支付链接后的查询参数
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,  # 马上要支付的订单编号
            total_amount=str(order_model.total_amount),  # 支付总金额, 要转换类型, 无法识别Decimal, 尽量使用字符串
            subject="my shop %s" % order_id,  # 标题
            return_url="https://www.myshop.com",  # 支付成功后的回调url
        )
        # 拼接好支付链接
        alipay_url = settings.ALIPAY_URL + "?" + order_string
        # 响应
        return Response({"alipay_url": alipay_url})


class PaymentStatusView(APIView):
    """修改订单状态, 保存支付宝交易号"""
    def put(self, request):
        # 获取前端以查询字符串的方式传入数据
        query_dict = request.query_params

        # 将query_dict转成字典(要将中间的sign移除，进行验证)
        data = query_dict.dict()
        sign = data.pop("sign")

        # 创建alipay支付宝对象
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            app_private_key_string="app_private_key_string",
            alipay_public_key_string="alipay_public_key_string",
            sign_type="RSA2",  # RSA 或 RSA2, 推荐RSA2更加安全
            debug=True,  # 默认False
        )
        # 调用alipay SDK中 verify方法进行验证支付结果，看结果是否是支付宝回复的
        success = alipay.verify(data=data, signature=sign)
        if not success:
            return Response({"msg": "非法请求"}, status=status.HTTP_403_FORBIDDEN)
        # 取出没多商城订单编号，再取出支付宝交易号
        order_id = data.get("out_trade_no")  # 订单编号
        trade_no = data.get("trade_no")  # 支付宝交易号
        # 把两个编号绑定到一起存储到mysql
        Payment.objects.create(
            order_id=order_id,
            trade_id=trade_no,
        )
        # 修改支付成功后的订单状态
        OrderInfo.objects.filter(order_id=order_id, status=OrderInfo.ORDER_STATUS_ENUM["UNPAID"])\
            .update(status=OrderInfo.ORDER_STATUS_ENUM["UNSEND"])

        # 响应
        return Response({"trade_id": trade_no}, status=status.HTTP_200_OK)
