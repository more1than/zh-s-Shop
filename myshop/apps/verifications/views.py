from random import randint
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_redis import get_redis_connection
import logging
from . import contants
from celery_tasks.sms.tasks import send_sms_code

logger = logging.getLogger("django")


class SMSCodeView(APIView):
    """短信验证"""

    def get(self, request, mobile):
        # 1. 创建redis连接对象
        redis_conn = get_redis_connection("verify_codes")
        # 2  从redis获取发送短信标记位
        send_flag = redis_conn.get("send_flag_%s" % mobile)
        if send_flag:  # 如果取到了标记位，证明60s已经发送了短信
            return Response({"message": "手机频繁发送短信"}, status=status.HTTP_400_BAD_REQUEST)
        # 3. 生成验证码
        # %06d 代表数位不足时前面的字符用0补全
        sms_code = "%06d" % randint(0, 999999)
        logger.info(sms_code)
        # 4. 把验证码存储到redis数据库
        # param1: redis key名
        # param2: 过期时间
        # param3: redis value值
        # 创建redis管道:(把多次redis操作装入管道中，将来一次性去执行，减少redis连接操作)
        pl = redis_conn.pipeline()
        pl.setex("sms_%s" % mobile, contants.SMS_CODE_REDIS_EXPIRES, sms_code)
        # 5 存储一个标记位，表示该手机号是否在60秒内发送过短信
        pl.setex("send_flag_%s" % mobile, contants.SEND_SMS_CODE_INTERVAL, 1)
        # 执行管道
        pl.execute()
        # 6. 利用xx工具发送短信验证码
        # 触发异步任务，将异步任务添加到celery任务队列
        # send_sms_code(mobile, sms_code)  # 普通调用函数
        send_sms_code.delay(mobile, sms_code)  # 触发异步任务
        # 7. 响应
        return Response({"message": "ok"})
