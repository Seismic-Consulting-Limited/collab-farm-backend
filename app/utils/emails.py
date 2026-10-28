import html
import os
from urllib.parse import quote

import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks
from pydantic import EmailStr

load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


async def _send_brevo_email(
    email_to: str,
    subject: str,
    html_content: str,
    recipient_name: str | None = None,
) -> None:
    raw_api_key = os.getenv("BREVO_API_KEY", "")
    api_key = raw_api_key.strip()
    wrapped_in_quotes = (
        len(raw_api_key) >= 2
        and raw_api_key[0] in ("'", '"')
        and raw_api_key[-1] == raw_api_key[0]
    )
    print(
        "[TEMP DEBUG] BREVO_API_KEY state: "
        f"present={bool(raw_api_key)}, "
        f"raw_length={len(raw_api_key)}, trimmed_length={len(api_key)}, "
        f"wrapped_in_quotes={wrapped_in_quotes}, "
        f"has_outer_whitespace={raw_api_key != raw_api_key.strip()}"
    )
    if not api_key:
        raise RuntimeError("BREVO_API_KEY is not configured.")

    sender_email = os.getenv("BREVO_SENDER_EMAIL", "rotneng@gmail.com").strip()
    sender_name = os.getenv("BREVO_SENDER_NAME", "CollabFarm").strip()

    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": str(email_to), **({"name": recipient_name} if recipient_name else {})}],
        "subject": subject,
        "htmlContent": html_content,
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            BREVO_API_URL,
            headers={
                "accept": "application/json",
                "api-key": api_key,
                "content-type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()


async def send_welcome_email(
    email_to: EmailStr,
    first_name: str | None = None,
    background_tasks: BackgroundTasks | None = None,
) -> None:
    display_name = html.escape(first_name or str(email_to))
    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
        <h2>Welcome to CollabFarm, {display_name}!</h2>
        <p>Thank you for joining our platform. We're thrilled to have you onboard.</p>
        <p>You can now explore agricultural investment opportunities and manage your portfolio seamlessly.</p>
        <br/>
        <p>Best regards,<br/><strong>The CollabFarm Team</strong></p>
    </div>
    """
    if background_tasks is not None:
        background_tasks.add_task(
            _send_brevo_email,
            str(email_to),
            "Welcome to CollabFarm!",
            html_content,
            first_name,
        )
        return

    await _send_brevo_email(
        str(email_to),
        "Welcome to CollabFarm!",
        html_content,
        first_name,
    )


def send_verification_email_background(
    email: str, token: str, background_tasks: BackgroundTasks
) -> None:
    verification_otp = html.escape(token)
    html_content = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2>Verify Your Email Address</h2>
        <p>Thank you for signing up with CollabFarm! Please use the code below to verify your email:</p>
        <p style="margin-top: 20px;">
            <h1 style="background-color: #2e7d32; color: #ffffff; padding: 10px 18px; border-radius: 4px; display: inline-block;">
                {verification_otp}
            </h1>
        </p>
        <p style="font-size: 12px; color: #777;">This code will expire in 6 minutes. If you did not create an account, please ignore this email.</p>
    </div>
    """
    background_tasks.add_task(
        _send_brevo_email,
        email,
        "Verify Your Email - CollabFarm",
        html_content,
    )


def send_reset_email_background(
    email: str, token: str, background_tasks: BackgroundTasks
) -> None:
    reset_link = f"{FRONTEND_URL}/reset-password?token={quote(token, safe='')}"
    escaped_token = html.escape(token)
    escaped_reset_link = html.escape(reset_link, quote=True)
    html_content = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2>Password Reset Request</h2>
        <p>You requested a password reset for your CollabFarm account.</p>
        <p><strong>Your Reset Token:</strong></p>
        <div style="background-color: #f4f4f4; padding: 12px; font-family: monospace; font-size: 14px; word-break: break-all; border-radius: 4px; border: 1px solid #ddd;">
            {escaped_token}
        </div>
        <p style="margin-top: 20px;">Click the button below to set a new password:</p>
        <p>
            <a href="{escaped_reset_link}" style="background-color: #2e7d32; color: #ffffff; padding: 10px 18px; text-decoration: none; border-radius: 4px; display: inline-block;">
                Reset Password
            </a>
        </p>
        <p style="font-size: 12px; color: #777;">If you did not make this request, please ignore this email.</p>
    </div>
    """
    background_tasks.add_task(
        _send_brevo_email,
        email,
        "Password Reset Request",
        html_content,
    )
