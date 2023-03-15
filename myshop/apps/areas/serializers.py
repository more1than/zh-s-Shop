from rest_framework import serializers
from areas.models import Area


class AreaSerializer(serializers.ModelSerializer):
    """省级的序列化器"""

    class Meta:
        model = Area
        fields = ["id", "name"]


class SubsSerializer(serializers.ModelSerializer):
    """详情视图使用的序列化器"""
    subs = AreaSerializer(many=True)

    # subs = serializers.PrimaryKeyRelatedField()  # 只会序列化出id
    # subs = serializers.StringRelatedField()  # 获取序列化时模型中str方法返回值

    class Meta:
        model = Area
        fields = ["id", "name", "subs"]
