import re
from .models import User

from django.contrib.auth.backends import ModelBackend


def jwt_response_payload_handler(token, user=None, request=None):
    """重写JWT登录视图的构造响应数据函数，多追加user_id和username"""
    return {
        "token": token,
        "user_id": user.id,
        "user_name": user.username,
    }


def get_user_by_account(account):
    """
    通过传入的账号动态获取user 模型对象
    :param account: 有可能是手机号，有可能是用户名
    :return user or None
    """
    try:
        # 匹配手机号成功证明是使用手机号注册，优先匹配手机号
        if re.match(r"^1[3-9]\d{9}$", account):
            user = User.objects.get(mobile=account)
        else:
            user = User.objects.get(username=account)
    except User.DoesNotExist:
        return None  # 未查询到返回None
    else:
        return user  # 返回模型实例化对象，而不是模型类


class UsernameMobileAuthBackend(ModelBackend):
    """修改Django认证类，为了实现多账号登录"""

    def authenticate(self, request, username=None, password=None, **kwargs):
        # 获取到user对象
        user = get_user_by_account(username)

        # 判断当前前端传入的密码是否正确
        if user and user.check_password(password):
            # 返回user对象
            return user
