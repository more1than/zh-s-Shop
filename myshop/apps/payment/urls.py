from django.urls import re_path

from . import views

urlpatterns = [
    # 获取支付宝支付url
    re_path(r"^orders/(?P<order_id>\d+)/payment/$", views.PaymentView.as_view()),

    # 支付后验证状态
    re_path(r"^payment/status/$", views.PaymentStatusView.as_view()),
]
