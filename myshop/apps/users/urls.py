from django.urls import path, re_path
from rest_framework import routers
from rest_framework_jwt.views import obtain_jwt_token

from . import views

urlpatterns = [
    # 用户注册
    re_path(r"^users/$", views.UserView.as_view()),
    # 判断用户名是否已注册
    re_path(r"^users/(?P<username>\w{5,20})/count/$", views.UsernameCountView.as_view()),
    # 判断手机号是否已注册
    re_path(r"^mobiles/(?P<mobile>1[3-9]\d{9})/count/$", views.MobileCountView.as_view()),
    # JWT登录, 内部认证逻辑是使用Django的, 额外登录成功生成token
    # re_path(r"authorizations/$", obtain_jwt_token),
    re_path(r"authorizations/$", views.UserAuthorizeView.as_view()),

    # 获取用户详情
    re_path(r"^user/$", views.UserDetailView.as_view()),
    # 更新邮箱
    re_path(r"^email/$", views.EmailView.as_view()),
    # 更新邮箱
    re_path(r"^email/verification/$", views.EmailVerifyView.as_view()),

    # 商品浏览记录
    re_path(r"^browse_histories/$", views.UserBrowserHistoryView.as_view()),
]

router = routers.DefaultRouter()
# 用户添加地址
router.register(r"addresses", views.AddressViewSet, basename="addresses")
urlpatterns += router.urls
