from django.urls import path, re_path
from rest_framework.routers import DefaultRouter

from . import views

urlpatterns = [
    # 省信息
    # re_path(r"^areas/$", views.AreaListView.as_view()),
    #
    # re_path(r"^areas/(?P<pk>\d+)/$", views.AreaDetailView.as_view()),
]

router = DefaultRouter()
# 如果视图集中没有给queryset类属性执行查询集，如果不传参默认取queryset中指定的查询集类名小写
router.register(r"areas", views.AreaViewSet, basename="area")
urlpatterns += router.urls
