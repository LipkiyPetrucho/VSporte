import os
from io import BytesIO

import weasyprint
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from orders.models import Order


@shared_task
def payment_completed(order_id):
    """
    Задание по отправке уведомления по электронной почте
    при успешной оплате заказа.
    """
    order = Order.objects.get(id=order_id)
    # create invoice e-mail
    subject = f"My Shop - Invoice no. {order.id}"
    message = "Please, find attached the invoice for your recent purchase."
    email = EmailMessage(subject, message, "pafos.light@yandex.ru", [order.email])
    # сгенерировать PDF
    html = render_to_string("orders/order/pdf.html", {"order": order})
    out = BytesIO()
    css_path = os.path.join(settings.STATIC_ROOT, "css", "pdf.css")
    stylesheets = [weasyprint.CSS(css_path)]
    weasyprint.HTML(string=html).write_pdf(out, stylesheets=stylesheets)
    # прикрепить PDF-файл
    email.attach(f"order_{order.id}.pdf", out.getvalue(), "application/pdf")
    # отправить электронное письмо
    email.send()
