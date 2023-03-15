import os

from celery import Celery

# 指定django的配置文件, 让celery也可以使用settings中的配置
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myshop.settings.dev')

# 1.创建celery实例对象
celery_app = Celery("my_shop")

# 2.加载配置文件
celery_app.config_from_object("celery_tasks.config")

# 3.自动注册异步任务
celery_app.autodiscover_tasks(["celery_tasks.sms", "celery_tasks.email", "celery_tasks.html"])
