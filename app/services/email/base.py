# app/services/email/base.py
"""
Abstract base class for email services.

This module defines the interface that all email service implementations must follow.
"""

from abc import ABC, abstractmethod


class EmailService(ABC):
    """
    Abstract base class for email services.

    This allows swapping between different email providers (Gmail, SendGrid, SES)
    without changing the code that uses the email service.
    """

    @abstractmethod
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool = False,
    ) -> None:
        """
        Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Email body content (plain text or HTML)
            html: If True, body is treated as HTML; otherwise plain text

        Raises:
            EmailSendError: If email sending fails
        """
        pass
