import re

from django_redis import get_redis_connection
from rest_framework import serializers
from .models import User, Address
from rest_framework_jwt.settings import api_settings
from celery_tasks.email.tasks import send_verify_email
from goods.models import SKU


class CreateUserSerializer(serializers.ModelSerializer):
    """注册序列化器"""

    # 序列化器需要校验的所有字段:[id, username, password, password2, mobile, sms_code, allow]
    # 需要校验的字段:[username, password, password2, mobile, sms_code, allow]
    # 模型中已存在的字段:[username, password, mobile]

    # 需要序列化的字段:[id, username, mobile]
    # 需要反序列化的字段:[username, password, password2, mobile, sms_code, allow]
    password2 = serializers.CharField(label="确认密码", write_only=True)
    sms_code = serializers.CharField(label="验证码", write_only=True)
    allow = serializers.CharField(label="同意协议", write_only=True)
    token = serializers.CharField(label="token", read_only=True)

    class Meta:
        model = User  # 从模型中映射序列化器字段
        fields = ["id", "username", "password", "password2", "mobile", "sms_code", "allow", "token"]
        extra_kwargs = {  # 限制字段入参
            "username": {
                "min_length": 5,
                "max_length": 20,
                "error_messages": {  # 自定义校验出错后的错误信息提示
                    "min_length": "仅允许5-20个字符的用户名",
                    "max_length": "仅允许5-20个字符的用户名",
                }
            },
            "password": {
                "write_only": True,
                "min_length": 8,
                "max_length": 20,
                "error_messages": {
                    "min_length": "仅允许8-20个字符的密码",
                    "max_length": "仅允许8-20个字符的密码",
                }
            }
        }

    def validate_mobile(self, value):
        """单独校验手机号"""
        if not re.match(r'1[3-9]\d{9}$', value):
            raise serializers.ValidationError("手机号格式有误")
        return value

    def validate_allow(self, value):
        """协议字段校验"""
        if value != "true":
            raise serializers.ValidationError("请同意用户协议")
        return value

    def validate(self, attrs):
        """校验密码是否相同"""
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError("两次密码不一致")

        # 校验验证码
        redis_conn = get_redis_connection("verify_codes")
        mobile = attrs["mobile"]
        real_sms_code = redis_conn.get("sms_%s" % mobile)

        # 向redis存储数据时都是以字符串进行存储的，取出来之后都是byte类型
        if real_sms_code is None or attrs["sms_code"] != real_sms_code.decode():
            raise serializers.ValidationError("验证码错误")
        return attrs

    def create(self, validated_data):
        # 部分信息无需入库
        del validated_data["password2"]
        del validated_data["sms_code"]
        del validated_data["allow"]

        # 密码加密
        password = validated_data.pop("password")

        user = User(**validated_data)
        user.set_password(password)  # 把加密后的密码赋值给user中的password属性
        user.save()  # 入库

        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_DECODE_HANDLER

        # 根据user信息生成载荷部分
        payload = jwt_payload_handler(user)
        # 根据payload生成token
        token = jwt_encode_handler(payload)

        user.token = token
        return user


class UserDetailSerializer(serializers.ModelSerializer):
    """用户详情序列化器"""

    class Meta:
        model = User
        fields = ['id', "username", "mobile", "email", "email_active"]


class EmailSerializer(serializers.ModelSerializer):
    """更新邮箱序列化器"""

    class Meta:
        model = User
        fields = ["id", "email"]
        extra_kwargs = {
            "email": {
                "required": True,
            }
        }

    def update(self, instance, validated_data):
        """重写此方法目的不是为了修改，而是借用此时机，发激活邮件"""
        instance.email = validated_data.get("email")
        instance.save()

        # 将来在此处写发送邮件功能
        # send_mail()

        # 设置用户的校验连接，包含在短信中一并发出
        verify_url = instance.generate_email_verify_url()
        send_verify_email.delay(instance.email, verify_url=verify_url)
        return instance


class UserAddressSerializer(serializers.ModelSerializer):
    """用户地址序列化器"""
    province = serializers.StringRelatedField(read_only=True)
    city = serializers.StringRelatedField(read_only=True)
    district = serializers.StringRelatedField(read_only=True)
    province_id = serializers.IntegerField(label="省ID", required=True)
    city_id = serializers.IntegerField(label="市ID", required=True)
    district_id = serializers.IntegerField(label="区ID", required=True)

    class Meta:
        model = Address
        exclude = ("user", "is_deleted", "create_time", "update_time")

    def validate_mobile(self, attrs):
        """验证手机号"""
        if not re.match(r"^1[3-9]\d{9}$", attrs):
            raise serializers.ValidationError("手机号格式错误")
        return attrs

    def create(self, validated_data):
        # GenericAPIView及其子类才可以获取到这三个值
        # self.context["format"]
        # self.context["request"] 获取用户模型对象
        # self.context["view"]
        user = self.context["request"].user
        validated_data["user"] = user
        return Address.objects.create(**validated_data)


class AddressTitleSerializer(serializers.ModelSerializer):
    """标题序列化器"""

    class Meta:
        model = Address
        fields = ("title",)


class UserBrowserHistorySerializer(serializers.Serializer):
    """保存商品浏览记录序列化器"""
    sku_id = serializers.IntegerField(label="商品sku_id", min_value=1)

    def validate_sku_id(self, attrs):
        """单独校验sku_id字段"""
        try:
            SKU.objects.get(id=attrs)
        except SKU.DoesNotExist:
            raise serializers.ValidationError("sku_id字段无效")
        return attrs

    def create(self, validated_data):
        sku_id = validated_data.get("sku_id")
        # 序列化器中获取当前的用户模型对象
        user = self.context["request"].user
        # 创建redis连接对象
        redis_conn = get_redis_connection("history")
        # 创建redis管道
        pl = redis_conn.pipeline()
        # 去重
        pl.lrem("history_%d" % user.id, 0, sku_id)
        # 添加到列表左侧
        pl.lpush("history_%d" % user.id, sku_id)
        # 截取前5个元素
        pl.ltrim("history_%d" % user.id, 0, 5)
        # 执行管道
        pl.execute()
        return validated_data


class SKUSerializer(serializers.ModelSerializer):
    """SKU商品序列化器"""

    class Meta:
        model = SKU
        fields = ['id', "name", 'price', "default_image_url", "comments"]
