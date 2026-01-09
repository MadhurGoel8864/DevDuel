# app/services/email/__init__.py
"""
Email service module.

Provides a singleton email service instance for use throughout the application.
"""

from app.services.email.gmail import GmailEmailService

# Singleton email service instance
email_service = GmailEmailService()

__all__ = ["email_service"]
