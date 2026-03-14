"""
Password reset email template.

This module provides the email template for password reset requests.
"""


def password_reset_email_template(reset_token: str) -> tuple[str, str]:
    """
    Generate password reset email template.

    Args:
        reset_token: The password reset token to include in the email

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
            .token-box {{
                background-color: #ffffff;
                border: 2px solid #e74c3c;
                border-radius: 8px;
                padding: 20px;
                text-align: center;
                margin: 30px 0;
            }}
            .token-code {{
                font-size: 18px;
                font-weight: bold;
                color: #e74c3c;
                word-break: break-all;
                margin: 10px 0;
                padding: 10px;
                background-color: #fef5f5;
                border-radius: 4px;
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
            .info {{
                background-color: #d1ecf1;
                border-left: 4px solid #17a2b8;
                padding: 15px;
                margin: 20px 0;
                border-radius: 4px;
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
                <h1>🔑 Password Reset Request</h1>
            </div>

            <p>Hello,</p>

            <p>We received a request to reset your password. Use the token below to reset your password:</p>

            <div class="token-box">
                <div style="color: #7f8c8d; font-size: 14px; margin-bottom: 10px;">YOUR RESET TOKEN</div>
                <div class="token-code">{reset_token}</div>
                <div style="color: #7f8c8d; font-size: 14px; margin-top: 10px;">Valid for 15 minutes</div>
            </div>

            <div class="info">
                <strong>How to reset your password:</strong>
                <ol style="margin: 10px 0;">
                    <li>Copy the reset token above</li>
                    <li>Go to the password reset page</li>
                    <li>Enter this token and your new password</li>
                    <li>Submit to complete the reset</li>
                </ol>
            </div>

            <div class="warning">
                <div class="warning-title">⚠️ Security Warning</div>
                <div>
                    Never share this reset token with anyone. Our team will never ask for your reset token.
                    If you didn't request a password reset,
                    please ignore this email and your password will remain unchanged.
                </div>
            </div>

            <p>This reset token will expire in <strong>15 minutes</strong>.
            If you didn't request a password reset, you can safely ignore this email.</p>

            <div class="footer">
                <p>This is an automated message, please do not reply to this email.</p>
                <p>&copy; 2026 DevDual. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return subject, html_body
