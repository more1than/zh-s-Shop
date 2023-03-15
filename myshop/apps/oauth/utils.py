from itsdangerous import TimedJSONWebSignatureSerializer, BadData
from django.conf import settings


def generate_save_user_token(openid):
    """对openid进行加密"""
    # 1. 创建加密的序列化器对象
    serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, 600)

    # 2. 调用dumps进行加密,加密后的数据默认是bytes类型
    data = {"openid": openid}
    token = serializer.dumps(data)

    # 3. 把加密后的openid返回
    return token.decode()


def check_save_user_token(access_token):
    """传入加密的openid进行解密并返回"""
    # 1. 创建加密的序列化器对象
    serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, 600)

    # 2. 调用loads方法解密
    try:
        data = serializer.loads(access_token)
    except BadData:
        return None
    else:
        return data.get("openid")
