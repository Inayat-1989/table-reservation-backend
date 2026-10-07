import time

from celery import shared_task
from django.core.mail import send_mail

from reservations.services.email_service import (
    send_reservation_otp_email,
)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_reservation_otp_email_task(
    self,
    *,
    recipient_email,
    customer_name,
    otp,
    reservation_reference,
    expires_at,
):
    send_reservation_otp_email(
        recipient_email=recipient_email,
        customer_name=customer_name,
        otp=otp,
        reservation_reference=reservation_reference,
        expires_at=expires_at,
    )


from celery import shared_task


@shared_task(bind=True)  # 1. Add bind=True here
def sendMail(
    self,  # 2. Add 'self' as the very first argument
    receipient_email,
    otp,
):
    start_time = time.time()

    send_mail(
        "Your OTP Code",
        f"Your code is {otp}",
        "from@example.com",
        [receipient_email],
    )
    print(f"--- Email network call took: {time.time() - start_time} seconds ---")
