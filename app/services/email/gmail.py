# app/services/email/gmail.py
"""
Gmail SMTP email service implementation.

This module provides email sending functionality using Gmail's SMTP server.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings
from app.services.email.base import EmailService

logger = logging.getLogger(__name__)


class EmailSendError(Exception):
    """Raised when email sending fails."""

    pass


# Stratergy Design Pattern
class GmailEmailService(EmailService):
    """
    Gmail SMTP email service implementation.

    Uses Gmail's SMTP server with STARTTLS for secure email delivery.
    """

    def __init__(self):
        """Initialize Gmail email service with configuration from settings."""
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.email_from = settings.email_from

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool = False,
    ) -> None:
        """
        Send an email via Gmail SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Email body content (plain text or HTML)
            html: If True, body is treated as HTML; otherwise plain text

        Raises:
            EmailSendError: If email sending fails
        """
        # Validate SMTP configuration
        if not self.smtp_username or not self.smtp_password or not self.email_from:
            logger.error("SMTP credentials not configured")
            raise EmailSendError(
                "Email service is not configured. Please set SMTP_USERNAME, "
                "SMTP_PASSWORD, and EMAIL_FROM in your .env file."
            )

        try:
            # Create message container
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.email_from
            msg["To"] = to_email

            # Attach body content
            mime_type = "html" if html else "plain"
            msg.attach(MIMEText(body, mime_type))

            # Connect to SMTP server and send email
            logger.info(f"Connecting to SMTP server: {self.smtp_host}:{self.smtp_port}")

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()  # Upgrade connection to secure
                logger.info(f"Authenticating as: {self.smtp_username}")
                server.login(self.smtp_username, self.smtp_password)

                logger.info(f"Sending email to: {to_email}")
                server.send_message(msg)

            logger.info(f"Email sent successfully to: {to_email}")

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            raise EmailSendError(
                "Failed to authenticate with SMTP server. "
                "Please check your SMTP credentials."
            ) from e

        except smtplib.SMTPException as e:
            logger.error(f"SMTP error occurred: {e}")
            raise EmailSendError(f"Failed to send email via SMTP: {e}") from e

        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            raise EmailSendError(f"Failed to send email: {e}") from e
