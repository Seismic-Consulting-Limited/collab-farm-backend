# app/utils/emails.py
import os
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from fastapi import BackgroundTasks
from pydantic import EmailStr

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""),
    MAIL_FROM=os.getenv("MAIL_FROM", "noreply@collabfarm.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)


async def send_welcome_email(
    email_to: EmailStr,
    first_name: str | None = None
):
    display_name = first_name if first_name else email_to

    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
        <h2>Welcome to CollabFarm {display_name}!</h2>
        <p>Thank you for joining our platform. We're thrilled to have you onboard.</p>
        <p>You can now explore agricultural investment opportunities and manage your portfolio seamlessly.</p>
        <br/>
        <p>Best regards,<br/><strong>The CollabFarm Team</strong></p>
    </div>
    """

    message = MessageSchema(
        subject="Welcome to CollabFarm!",
        recipients=[email_to],
        body=html_content,
        subtype=MessageType.html,
    )

    fm = FastMail(conf)
    await fm.send_message(message)


def send_reset_email_background(email: str, token: str, background_tasks: BackgroundTasks):
    reset_link = f"https://localhost:8000/auth/reset-password?token={token}"

    message = MessageSchema(
        subject="Password Reset Request - CollabFarm",
        recipients=[email],
        body=f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Password Reset Request</h2>
            <p>You requested a password reset for your CollabFarm account.</p>
            
            <p><strong>Your Reset Token:</strong></p>
            <div style="background-color: #f4f4f4; padding: 12px; font-family: monospace; font-size: 14px; word-break: break-all; border-radius: 4px; border: 1px solid #ddd;">
                {token}
            </div>

            <p style="margin-top: 20px;">Or click the link below to set a new password directly (valid for 1 hour):</p>
            <p>
                <a href="{reset_link}" style="background-color: #2e7d32; color: #ffffff; padding: 10px 18px; text-decoration: none; border-radius: 4px; display: inline-block;">
                    Reset Password
                </a>
            </p>
            
            <p style="font-size: 12px; color: #777;">
                Direct Link: <a href="{reset_link}">{reset_link}</a>
            </p>
            <p style="font-size: 12px; color: #777;">If you did not make this request, please ignore this email.</p>
        </div>
        """,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message)
