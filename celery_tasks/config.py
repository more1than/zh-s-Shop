# celery配置文件
from celery import app
from django.conf import settings

# 指定任务队列的位置
broker_url = "redis://127.0.0.1:6379/7"
