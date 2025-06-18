from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from typing import Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

email_config = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM", "noreply@zerodhamirror.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)

fastmail = FastMail(email_config)

async def send_invite_email(
    email_to: EmailStr,
    invite_data: Dict[str, Any]
) -> None:
    """
    Send an invite email to a user
    """
    # Create invite URL
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    invite_url = f"{frontend_url}/invite/{invite_data['invite_token']}"
    
    # Create email body
    body = f"""
    <h2>You've been invited to join {invite_data['group_name']}!</h2>
    <p>You've been invited to join a trading group on Zerodha Mirror.</p>
    <p>Group Details:</p>
    <ul>
        <li><strong>Group Name:</strong> {invite_data['group_name']}</li>
        {'<li><strong>Description:</strong> ' + invite_data['group_description'] + '</li>' if invite_data.get('group_description') else ''}
    </ul>
    <p>Click the button below to join the group:</p>
    <a href="{invite_url}" style="display: inline-block; background-color: #4F46E5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; margin: 16px 0;">
        Accept Invite
    </a>
    <p>Or copy and paste this URL into your browser:</p>
    <p>{invite_url}</p>
    <p>If you don't want to join this group, you can ignore this email.</p>
    """

    message = MessageSchema(
        subject=f"Invitation to join {invite_data['group_name']} on Zerodha Mirror",
        recipients=[email_to],
        body=body,
        subtype="html"
    )

    await fastmail.send_message(message) 