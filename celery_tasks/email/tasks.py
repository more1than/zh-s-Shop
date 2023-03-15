from django.conf import settings
from django.core.mail import send_mail

from celery_tasks.main import celery_app


@celery_app.task(name="send_verify_email")
def send_verify_email(to_email, verify_url):
    """
    发激活邮箱的邮件
    :param to_email: 收件人邮箱
    :param verify_url: 邮件激活url
    :return:
    """
    subject = 'my_shop邮件验证'  # 邮件主题
    html_message = '<p>尊敬的用户您好！</p>' \
                   '<p>感谢您使用my_shop。</p>' \
                   '<p>您的邮箱为: %s。请点击此连接激活您的邮箱：</p>' \
                   '<p><a href="%s">%s<a></p>' % (to_email, verify_url, verify_url)
    # send_mail(subject:标题, message:普通邮件正文, 发件人, [收件人列表], html_message=超文本的邮件内容)
    send_mail(subject, "", settings.EMAIL_FROM, [to_email], html_message=html_message)
