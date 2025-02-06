from celery import shared_task
from django.core.mail import send_mail
from .models import Order
import logging

logger = logging.getLogger(__name__)


@shared_task
def order_created(order_id):
    """
    Задание по отправке уведомления по электронной почте
    при успешном создании заказа.
    """
    order = Order.objects.get(id=order_id)
    subject = f"Order nr. {order.id}"
    message = (
        f"Dear {order.first_name},\n\n"
        f"You have successfully placed an order."
        f"Your order ID is: {order.id}."
    )
    try:
        mail_sent = send_mail(subject, message, "pafos.light@yandex.ru", [order.email])
        logger.info(f"Email sent successfully to {order.email}")
        return mail_sent
    except Exception as e:
        logger.error(f"Failed to send email to {order.email}: {str(e)}")
        return False
