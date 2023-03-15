from datetime import datetime

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView, GenericAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_jwt.settings import api_settings
from rest_framework_jwt.views import ObtainJSONWebToken

from goods.models import SKU
from users.models import User, Address
from users.serializers import CreateUserSerializer, UserDetailSerializer, EmailSerializer, UserAddressSerializer, \
    AddressTitleSerializer, UserBrowserHistorySerializer, SKUSerializer
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import UpdateModelMixin
from django_redis import get_redis_connection
from carts.utils import merge_cart_cookie_to_redis

jwt_response_payload_handler = api_settings.JWT_RESPONSE_PAYLOAD_HANDLER


class UserView(CreateAPIView):
    serializer_class = CreateUserSerializer


class UsernameCountView(APIView):
    """判断用户是否已经注册"""

    def get(self, request, username):
        # 查询user表
        count = User.objects.filter(username=username).count()
        # 包装响应数据
        data = {
            "username": username,
            "count": count,
        }
        # 响应
        return Response(data)


class MobileCountView(APIView):
    """判断手机号是否已经注册"""

    def get(self, request, mobile):
        # 查询数据库
        count = User.objects.filter(mobile=mobile).count()
        # 构造响应数据
        data = {
            "mobile": mobile,
            "count": count
        }
        # 响应
        return Response(data)


class UserDetailView(RetrieveAPIView):
    """用户详细信息展示"""
    serializer_class = UserDetailSerializer
    # queryset = User.objects.all()
    # 执行权限， 直摇头通过认证的用户才能访问视图
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """重写get_object方法，返回用户模型对象"""
        return self.request.user


# PUT /email/pk
class EmailView(UpdateAPIView):
    """更新用户邮箱"""
    permission_classes = [IsAuthenticated]
    serializer_class = EmailSerializer

    def get_object(self):
        return self.request.user


class EmailVerifyView(APIView):
    """激活用户邮箱"""

    def get(self, request):
        # 获取前端传入的token
        token = request.query_params.get("token")
        if not token:
            return Response({"message": "缺少token"}, status=status.HTTP_400_BAD_REQUEST)
        # 解密token并查询对应的user
        user = User.check_email_verify_token(token)
        # 修改当前用户的email_active为true
        if user is None:
            return Response({"message": "激活失败"}, status=status.HTTP_400_BAD_REQUEST)
        user.email_active = True
        user.save()
        # 响应
        return Response({"message": "ok"})


class AddressViewSet(UpdateModelMixin, GenericViewSet):
    """用户收货地址增删改查"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserAddressSerializer

    def get_queryset(self):
        return self.request.user.addresses.filter(is_deleted=False)

    def create(self, request):
        user = request.user
        count = user.addresses.all().count()
        # count = Address.objects.filter(user=user).count()
        # 用户收货地址数量有上线
        if count >= 20:
            return Response({"message": "收货地址数量上限"}, status=status.HTTP_400_BAD_REQUEST)
        # 创建序列化器进行反序列化
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """用户地址数据"""
        queryset = self.queryset()
        serializer = self.get_serializer(queryset, many=True)
        user = self.request.user
        return Response({
            "user_id": user.id,
            "default_address_id": user.default_address,
            "limit": 20,
            "addresses": serializer.data
        })

    def destroy(self, request, *args, **kwargs):
        """处理删除"""
        address = self.get_object()

        address.is_deleted = True
        address.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=["put"], detail=True)
    def title(self, request, pk=None):
        """修改标题"""
        address = self.get_object()
        serializer = AddressTitleSerializer(instance=address, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(methods=["put"], detail=True)
    def status(self, request, pk=None):
        """设置默认地址"""
        address = self.get_object()
        request.user.default_address = address
        request.user.save()
        return Response({"message": "ok"}, status=status.HTTP_200_OK)


class UserBrowserHistoryView(CreateAPIView):
    """用户商品浏览记录"""
    # 指定序列化器
    permission_classes = [IsAuthenticated]
    serializer_class = UserBrowserHistorySerializer

    def get(self, request):
        """查询商品浏览记录"""
        # 创建redis链接对象
        redis_conn = get_redis_connection("history")
        # 获取redis中当前用户的浏览记录列表
        sku_ids = redis_conn.lrange("history_%d" % request.user.id, 0, -1)
        # 通过列表中sku_id获取sku模型
        # SKU.objects.filter(id__in=sku_ids)  此方法可以遍历获取集合中的元素进行查询，可是会打乱顺序(id__in)
        sku_list = []
        for sku_id in sku_ids:
            sku = SKU.objects.get(id=sku_id)
            sku_list.append(sku)
        # 创建序列化器进行序列化
        serializer = SKUSerializer(sku_list, many=True)
        # 响应
        return Response(serializer.data)


class UserAuthorizeView(ObtainJSONWebToken):
    """自定义账号密码登录视图，实现购物车登陆合并"""
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user = serializer.object.get('user') or request.user
            token = serializer.object.get('token')
            response_data = jwt_response_payload_handler(token, user, request)
            response = Response(response_data)
            if api_settings.JWT_AUTH_COOKIE:
                expiration = (datetime.utcnow() +
                              api_settings.JWT_EXPIRATION_DELTA)
                response.set_cookie(api_settings.JWT_AUTH_COOKIE,
                                    token,
                                    expires=expiration,
                                    httponly=True)
            merge_cart_cookie_to_redis(request, user, response)
            return response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
