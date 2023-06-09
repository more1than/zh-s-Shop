from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from itsdangerous import TimedJSONWebSignatureSerializer, BadData

from myshop.utils.models import BaseModel


class User(AbstractUser):
    """
    继承AbstractUser模型，django中定义好了用户身份认证等信息，仅需添加手机号字段
    自定义用户模型类，进一步封装
    """
    mobile = models.CharField(max_length=11, unique=True, verbose_name="手机号")
    email_active = models.BooleanField(default=False, verbose_name="邮箱激活状态")
    default_address = models.ForeignKey("Address", related_name="users", null=True, blank=True,
                                        on_delete=models.SET_NULL, verbose_name="默认地址")

    class Meta:  # 配置数据库表名，及设置模型在admin站点显示的中文名
        db_table = "tb_users"
        verbose_name = "用户"
        verbose_name_plural = verbose_name

    def generate_email_verify_url(self):
        """生成邮箱激活连接"""
        # 1. 创建加密的序列化器
        serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, 3600 * 24)
        # 2. 调用dumps方法进行加密，bytes
        data = {"user_id": self.id, "email": self.email}
        token = serializer.dumps(data).decode()

        return "http://www.myshop.site:8080/success_verify_email.html?token=" + token

    @staticmethod
    def check_email_verify_token(token):
        """对token解密，并查询对应的user"""
        # 1. 创建加密的序列化器
        serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, 3600 * 24)
        # 2. 调用loads解密
        try:
            data = serializer.loads(token)
        except BadData:
            return None
        else:
            id = data.get("user_id")
            email = data.get("email")
            try:
                user = User.objects.get(id=id, email=email)
            except User.DoseNotExist:
                return None
            else:
                return user


class Address(BaseModel):
    """用户地址"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses", verbose_name="用户")
    title = models.CharField(max_length=20, verbose_name="地址名称")
    receiver = models.CharField(max_length=20, verbose_name="收货人")
    province = models.ForeignKey("areas.Area", on_delete=models.PROTECT, related_name="province_addresses",
                                 verbose_name="省")
    city = models.ForeignKey("areas.Area", on_delete=models.PROTECT, related_name="city_addresses", verbose_name="市")
    district = models.ForeignKey("areas.Area", on_delete=models.PROTECT, related_name="district_addresses",
                                 verbose_name="区")
    place = models.CharField(max_length=50, verbose_name="地址")
    mobile = models.CharField(max_length=11, verbose_name="手机")
    tel = models.CharField(max_length=20, null=True, blank=True, default="", verbose_name="固定电话")
    email = models.CharField(max_length=30, null=True, blank=True, default="", verbose_name="电子邮箱")
    is_deleted = models.BooleanField(default=False, verbose_name="逻辑删除")

    class Meta:
        db_table = "tb_address"
        verbose_name = "用户地址"
        verbose_name_plural = verbose_name
        ordering = ["-update_time"]
