"""
Password reset email template.

This module provides the email template for password reset requests.
"""


def password_reset_email_template(reset_link: str) -> tuple[str, str]:
    """
    Generate password reset email template.

    Args:
        reset_link: Full frontend URL with the reset token as a query parameter

    Returns:
        tuple[str, str]: (subject, html_body)
    """
    subject = "Password Reset Request"

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
            .btn-container {{
                text-align: center;
                margin: 30px 0;
            }}
            .btn {{
                display: inline-block;
                padding: 14px 32px;
                background-color: #e74c3c;
                color: #ffffff !important;
                text-decoration: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }}
            .fallback-link {{
                word-break: break-all;
                color: #e74c3c;
                font-size: 13px;
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
                <h1>Password Reset Request</h1>
            </div>

            <p>Hello,</p>

            <p>We received a request to reset your DevDuel password. Click the button below to choose a new password:</p>

            <div class="btn-container">
                <a href="{reset_link}" class="btn">Reset My Password</a>
            </div>

            <p style="text-align: center; color: #7f8c8d; font-size: 13px;">
                This link expires in <strong>15 minutes</strong>.
            </p>

            <p style="font-size: 13px; color: #555;">
                If the button above doesn't work, copy and paste this link into your browser:
            </p>
            <p class="fallback-link">{reset_link}</p>

            <div class="warning">
                <div class="warning-title">Security Notice</div>
                <div>
                    If you didn't request a password reset, you can safely ignore this email —
                    your password will remain unchanged.
                    Never share this link with anyone.
                </div>
            </div>

            <div class="footer">
                <p>This is an automated message, please do not reply to this email.</p>
                <p>&copy; 2026 DevDual. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return subject, html_body
