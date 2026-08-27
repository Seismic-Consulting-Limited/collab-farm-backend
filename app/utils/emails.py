import os
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
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


async def send_welcome_email(email_to: EmailStr | None = None):
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
        <h2>Welcome to CollabFarm, </h2>
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