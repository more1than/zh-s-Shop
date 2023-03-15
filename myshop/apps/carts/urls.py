from django.urls import re_path

from . import views

urlpatterns = [
    # 购物车增删改查
    re_path(r"^carts/$", views.CartView.as_view()),

    # 购物车全选
    re_path(r"^carts/selection/$", views.CartSelectedAllView.as_view()),
]
