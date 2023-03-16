from django.urls import path, re_path

from . import views

urlpatterns = [
    # 去结算
    re_path(r"^orders/settlement/$", views.OrderSettlementView.as_view()),

    # 保存订单
    re_path(r"^orders/$", views.CommitOrderView.as_view()),
]
