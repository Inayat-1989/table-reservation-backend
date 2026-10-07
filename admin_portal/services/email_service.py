from django.conf import settings
from django.core.mail import EmailMultiAlternatives


def send_admin_otp_email(
    *,
    recipient_email,
    admin_name,
    otp,
    expires_at,
):
    """Send the admin portal verification OTP."""
    subject = "Your Admin Portal Verification Code"

    text_content = f"""
Hello {admin_name},

Your admin portal verification code is:

{otp}

This OTP expires at:
{expires_at.strftime("%Y-%m-%d %H:%M")}

Please do not share this code with anyone.

If you did not attempt to log in to the admin portal,
you can safely ignore this email.

Regards,
{settings.APP_NAME}
"""

    html_content = f"""
<html>
<body>
    <h2>Admin Portal Verification</h2>

    <p>Hello {admin_name},</p>

    <p>Your admin portal verification code is:</p>

    <h1>{otp}</h1>

    <p>
        This OTP expires at:
        {expires_at.strftime("%Y-%m-%d %H:%M")}
    </p>

    <p>
        Please do not share this code with anyone.
    </p>

    <p>
        If you did not attempt to log in to the admin portal,
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
