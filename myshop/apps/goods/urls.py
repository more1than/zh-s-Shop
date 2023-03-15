from django.urls import path, re_path
from . import views

urlpatterns = [
    # 商品列表数据查询
    re_path(r'^categories/(?P<category_id>\d+)/skus/', views.SKUListView.as_view()),
]
