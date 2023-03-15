from django.urls import path, re_path

from . import views

urlpatterns = [
    # 拼接QQ登录URL
    re_path(r"^qq/authorization/$", views.QQOauthURLView.as_view()),
    # 登录QQ后回调
    re_path(r"^qq/user/$", views.QQAuthUserView.as_view()),
]
