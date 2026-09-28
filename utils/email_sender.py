import os
import requests

RESEND_API_URL = "https://api.resend.com/emails"

# ─── DEFAULT SENDER ───
# Works without owning/verifying a domain in Resend — good enough to
# start with. Once you buy your domain and verify it inside Resend,
# change this to something like "Gleamwave <orders@gleamwave.com>"
# for a more professional-looking sender address.
DEFAULT_FROM = "Gleamwave <onboarding@resend.dev>"


def send_email(to_email, subject, html_body, from_email=None):
    """
    Send an email via Resend's HTTPS API.

    This replaces the old smtplib-based sending. Railway (and many other
    hosts) block outbound SMTP connections entirely, but this is a plain
    HTTPS request — nothing to block.

    Raises an exception on failure so callers can decide how to respond
    (e.g. still return a success response to the user since the order/OTP
    itself was saved, just log the email failure).
    """
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        raise Exception("RESEND_API_KEY is not configured")

    payload = {
        "from": from_email or DEFAULT_FROM,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    }

    response = requests.post(
        RESEND_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=15,
    )

    if response.status_code >= 400:
        raise Exception(f"Resend API error ({response.status_code}): {response.text}")

    result = response.json()
    print(f"Email sent via Resend to {to_email} — id: {result.get('id')}")
    return result