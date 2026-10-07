from celery import shared_task

from admin_portal.services.email_service import (
    send_admin_otp_email,
)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_admin_otp_email_task(
    self,
    *,
    recipient_email,
    admin_name,
    otp,
    expires_at,
):
    send_admin_otp_email(
        recipient_email=recipient_email,
        admin_name=admin_name,
        otp=otp,
        expires_at=expires_at,
    )
