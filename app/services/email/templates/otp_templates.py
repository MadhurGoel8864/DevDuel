# app/services/email/templates.py
"""
Email templates for various use cases.

This module provides functions to generate email content for different scenarios.
"""

from app.core.config import settings


def otp_email_template(otp: str) -> tuple[str, str]:
    """
    Generate OTP verification email template.

    Args:
        otp: The one-time password to include in the email

    Returns:
        tuple[str, str]: (subject, html_body)
    """
    subject = "Your OTP Verification Code"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .container {{
                background-color: #f9f9f9;
                border-radius: 8px;
                padding: 30px;
                border: 1px solid #e0e0e0;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .header h1 {{
                color: #2c3e50;
                margin: 0;
                font-size: 24px;
            }}
            .otp-box {{
                background-color: #ffffff;
                border: 2px solid #3498db;
                border-radius: 8px;
                padding: 20px;
                text-align: center;
                margin: 30px 0;
            }}
            .otp-code {{
                font-size: 36px;
                font-weight: bold;
                color: #3498db;
                letter-spacing: 8px;
                margin: 10px 0;
            }}
            .warning {{
                background-color: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .warning-title {{
                font-weight: bold;
                color: #856404;
                margin-bottom: 5px;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                font-size: 12px;
                color: #7f8c8d;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔐 Email Verification</h1>
            </div>

            <p>Hello,</p>

            <p>You have requested a one-time password (OTP) for verification.
            Please use the code below to complete your verification:</p>

            <div class="otp-box">
                <div style="color: #7f8c8d; font-size: 14px; margin-bottom: 10px;">YOUR OTP CODE</div>
                <div class="otp-code">{otp}</div>
                <div style="color: #7f8c8d; font-size: 14px; margin-top: 10px;">Valid for 5 minutes</div>
            </div>

            <div class="warning">
                <div class="warning-title">⚠️ Security Warning</div>
                <div>
                    Never share this OTP with anyone. Our team will never ask for your OTP.
                    If you didn't request this code, please ignore this email.
                </div>
            </div>

            <p>This OTP will expire in <strong>{settings.OTP_EXPIRE_SECONDS//60} minutes</strong>.
            If you didn't request this verification code, you can safely ignore this email.</p>

            <div class="footer">
                <p>This is an automated message, please do not reply to this email.</p>
                <p>&copy; 2026 DevDuel. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return subject, html_body
