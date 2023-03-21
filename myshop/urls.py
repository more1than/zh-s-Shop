"""myshop URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path

urlpatterns = [
    path('admin/', admin.site.urls),

    re_path(r"^", include("verifications.urls")),  # 发短信

    re_path(r"^", include("users.urls")),  # 用户模块

    re_path(r"^oauth/", include("oauth.urls")),  # qq模块

    re_path(r"^", include("areas.urls")),  # qq模块

    # re_path(r"^ckeditor/", include("ckeditor_uploader.urls")),  # 富文本编辑器

    re_path(r"^", include("goods.urls")),  # 商品模块

    re_path(r"^", include("carts.urls")),  # 购物车模块

    re_path(r"^", include("orders.urls")),  # 订单模块

    re_path(r"^", include("payment.urls")),  # 支付宝模块
]
