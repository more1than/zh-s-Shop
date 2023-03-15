import logging

from QQLoginTool.QQtool import OAuthQQ
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from rest_framework_jwt.settings import api_settings
from .utils import generate_save_user_token
from .serializers import QQAuthUserSerializer
from .models import OAuthQQUser
from carts.utils import merge_cart_cookie_to_redis


logger = logging.getLogger("django")


class QQOauthURLView(APIView):
    """拼接好QQ登录网址"""

    def get(self, request):
        # 1. 提取前端传入的next参数记录用户从哪里到login界面
        next = request.query_params.get("next") or "/"
        # # 登录参数
        # QQ_CLIENT_ID = "xxx"
        # QQ_CLIENT_SECRET = "xxx"
        # QQ_REDIRECT_URL = "xxx"
        # 2. 利用QQ登录SDK
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID, client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URL, state=next)
        # 创建QQ登录工具对象
        login_url = oauth.get_qq_url()
        # 调用里面的方法，拼接好QQ登录网址
        return Response({"login_url": login_url, })


class QQAuthUserView(APIView):
    """QQ登录成功后的回调处理"""

    def get(self, request):
        # 获取前端传入的code
        code = request.query_params.get("code")
        if not code:  # 如果没有获取到code
            return Response({"message": "缺少code"}, status=status.HTTP_400_BAD_REQUEST)

        # 创建QQ登录工具对象
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID, client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URL)
        try:
            # 调用get_access_token(code) 用code向QQ服务器获取access_token
            access_token = oauth.get_access_token(code)
            # 调用里面的get_open_id(access_token) 用access_token响应QQ服务器获取openid
            openid = oauth.get_open_id(access_token)

            if not openid:
                return Response({"message": "缺少openid"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.info(e)
            return Response({"message": "qq服务器不可用"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # 查询服务器中有无openid
        try:
            authQQUserModel = OAuthQQUser.objects.get(openid=openid)
        except OAuthQQUser.DoesNotExist:
            # 如果不存在openid 证明未绑定用户，把openid加密后响应给前端，让前端先暂存一会，等待绑定时使用
            access_token_openid = generate_save_user_token(openid)
            return Response({"access_token": access_token_openid})
        else:
            # 如果数据库中有openid，直接代码登陆成功，给前端jwt，状态保存信息
            user = authQQUserModel.user  # 获取到openid 关联的user

            jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
            jwt_encode_handler = api_settings.JWT_DECODE_HANDLER

            # 根据user信息生成载荷部分
            payload = jwt_payload_handler(user)
            # 根据payload生成token
            token = jwt_encode_handler(payload)

            response = Response({
                "token": token,
                "username": user.username,
                "user_id": user.id,
            })
            
            # 调用合并购物车函数
            merge_cart_cookie_to_redis(request, user, response)

            return response

    def post(self, request):
        """openid绑定用户接口"""
        # 创建序列化器进行反序列化
        serializer = QQAuthUserSerializer(data=request.data)
        # 调用序列化器的is_valid方法进行校验
        serializer.is_valid(raise_exception=True)
        # 调用序列化器的save方法
        user = serializer.save()
        # 生成JWT状态，保存token
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_DECODE_HANDLER

        # 根据user信息生成载荷部分
        payload = jwt_payload_handler(user)
        # 根据payload生成token
        token = jwt_encode_handler(payload)

        response = Response({
            "token": token,
            "username": user.name,
            "user_id": user.id
        })

        # 调用合并购物车函数
        merge_cart_cookie_to_redis(request, user, response)
        return response
