from django.conf import settings
from django.core.mail import EmailMultiAlternatives


def send_reservation_otp_email(
    *,
    recipient_email,
    customer_name,
    otp,
    reservation_reference,
    expires_at,
):
    """
    Send the reservation verification OTP to the customer.
    """

    subject = "Your Reservation Verification Code"

    text_content = f"""
Hello {customer_name},

Your reservation verification code is:

{otp}

Reservation reference:
{reservation_reference}

This OTP expires at:
{expires_at.strftime("%Y-%m-%d %H:%M")}

Please do not share this code with anyone.

If you did not make this reservation, you can safely ignore this email.

Regards,
{settings.APP_NAME}
"""

    html_content = f"""
<html>
<body>
    <h2>Reservation Verification</h2>

    <p>Hello {customer_name},</p>

    <p>Your reservation verification code is:</p>

    <h1>{otp}</h1>

    <p>
        <strong>Reservation reference:</strong>
        {reservation_reference}
    </p>

    <p>
        This OTP expires at:
        {expires_at.strftime("%Y-%m-%d %H:%M")}
    </p>

    <p>
        Please do not share this code with anyone.
    </p>

    <p>
        If you did not make this reservation,
        you can safely ignore this email.
    </p>

    <p>
        Regards,<br>
        {settings.APP_NAME}
    </p>
</body>
</html>
"""

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient_email],
    )

    email.attach_alternative(
        html_content,
        "text/html",
    )

    email.send(fail_silently=False)
