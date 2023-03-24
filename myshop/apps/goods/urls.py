from django.urls import path, re_path
from rest_framework.routers import DefaultRouter

from . import views

urlpatterns = [
    # 商品列表数据查询
    re_path(r'^categories/(?P<category_id>\d+)/skus/', views.SKUListView.as_view()),
]

router = DefaultRouter()
router.register("skus/search", views.SKUSearchViewSet, basename="skus_search")

urlpatterns += router.urls
