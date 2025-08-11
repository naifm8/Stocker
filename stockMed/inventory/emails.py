from django.core.mail import send_mail
from django.conf import settings

def send_inventory_alert(subject: str, message: str, to_emails=None) -> int:

    recipients = to_emails or ([settings.MANAGER_ALERT_EMAIL] if settings.MANAGER_ALERT_EMAIL else [])
    if not recipients:
        return 0
    return send_mail(
        subject=subject.strip(),
        message=message.strip(),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=False,
    )
