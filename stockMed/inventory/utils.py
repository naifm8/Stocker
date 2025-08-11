from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from django.utils import timezone
from .models import Product
from django.db.models import F

def send_inventory_alert(subject, message, recipient_list):
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        recipient_list,
        fail_silently=False,
    )

def get_inventory_alerts():
    today = timezone.now().date()
    near_expiry_date = today + timedelta(days=30)

    low_stock_products = Product.objects.filter(quantity_in_stock__lte=F('reorder_level'))
    near_expiry_products = Product.objects.filter(expiry_date__lte=near_expiry_date)

    return low_stock_products, near_expiry_products



