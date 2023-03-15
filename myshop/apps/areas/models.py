from django.db import models


class Area(models.Model):
    """省区"""
    name = models.CharField(max_length=20, verbose_name="名称")
    # 自关联的表, 外键指向自己   on_delete=models.SET_NULL允许为空
    # null数据库为空, blank表单为空
    # related_name='subs'
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, related_name="subs", null=True, blank=True,
                               verbose_name="上级行政区划")

    # 哈尔滨市.parent   表示拿到上级行政区黑龙江省
    # 反之：(黑龙江省.subs | 黑龙江省.area_set) 表示获取该省的下级所有市信息 一方调用多方的类名+_set可以获取多方的信息
    class Meta:
        db_table = "tb_areas"
        verbose_name = "行政区划"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name
