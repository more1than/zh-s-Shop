# 编辑异步任务代码
from time import sleep

from celery_tasks.main import celery_app


@celery_app.task(name="send_sms_code")  # 使用装饰器注册任务
def send_sms_code(mobile, code):
    print("发送短信, {0}, {1}".format(mobile, code))
    sleep(1)
