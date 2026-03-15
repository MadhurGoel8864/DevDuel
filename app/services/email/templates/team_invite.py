"""
Email templates for team invitations.
Two variants:
  - Registered user  → accept / decline buttons
  - New user         → register & join button
"""


def team_invite_registered_template(
    team_name: str,
    role: str,
    accept_url: str,
    decline_url: str,
    inviter_email: str,
    inviter_name: str | None,
    invitee_name: str | None,
) -> tuple[str, str]:
    """
    Invite email for an already-registered user.

    Returns:
        tuple[str, str]: (subject, html_body)
    """
    subject = f"You've been invited to join {team_name} on DevDuel"
    role_label = "Bidding Strategist" if role == "BIDDING" else "Coding Solver"
    role_color = "#9b59b6" if role == "BIDDING" else "#27ae60"
    role_icon = "🧠" if role == "BIDDING" else "💻"

    # Greeting: use invitee name if provided, otherwise generic
    greeting = f"Hello {invitee_name}," if invitee_name else "Hello,"

    # Inviter line: use name if available, otherwise just email
    if inviter_name:
        inviter_line = f'<strong>{inviter_name}</strong> (<a href="mailto:{inviter_email}" style="color:#3498db;">{inviter_email}</a>)'
    else:
        inviter_line = f'<a href="mailto:{inviter_email}" style="color:#3498db;">{inviter_email}</a>'

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                   line-height:1.6; color:#333; max-width:600px; margin:0 auto; padding:20px; }}
            .container {{ background:#f9f9f9; border-radius:8px; padding:30px; border:1px solid #e0e0e0; }}
            .header {{ text-align:center; margin-bottom:30px; }}
            .inviter-box {{ background:#eaf4fb; border-radius:8px; padding:15px 20px; margin:15px 0;
                           border-left:4px solid #3498db; }}
            .team-box {{ background:#fff; border:2px solid #3498db; border-radius:8px;
                        padding:20px; text-align:center; margin:25px 0; }}
            .team-name {{ font-size:22px; font-weight:bold; color:#2c3e50; margin-bottom:10px; }}
            .role-badge {{ display:inline-block; background:{role_color}; color:white;
                          padding:6px 16px; border-radius:20px; font-size:14px; font-weight:bold; }}
            .btn-accept {{ display:inline-block; background:#27ae60; color:white !important;
                          text-decoration:none; padding:14px 32px; border-radius:6px;
                          font-size:16px; font-weight:bold; margin:0 8px; }}
            .btn-decline {{ display:inline-block; background:#e74c3c; color:white !important;
                           text-decoration:none; padding:14px 32px; border-radius:6px;
                           font-size:16px; font-weight:bold; margin:0 8px; }}
            .warning {{ background:#fff3cd; border-left:4px solid #ffc107;
                       padding:15px; margin:20px 0; border-radius:4px; font-size:13px; }}
            .footer {{ text-align:center; margin-top:30px; font-size:12px; color:#7f8c8d; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header"><h1>⚔️ DevDuel Team Invitation</h1></div>
            <p>{greeting}</p>
            <div class="inviter-box">
                📩 <strong>Invited by:</strong> {inviter_line}
            </div>
            <p>You have been invited to join a team on <strong>DevDuel</strong>.</p>
            <div class="team-box">
                <div class="team-name">🏆 {team_name}</div>
                <div style="color:#7f8c8d; font-size:14px; margin-top:8px;">Your assigned role</div>
                <div class="role-badge">{role_icon} {role_label}</div>
            </div>
            <p>This invite expires in <strong>72 hours</strong>.</p>
            <div style="text-align:center; margin:30px 0;">
                <a href="{accept_url}" class="btn-accept">✅ Accept Invite</a>
                <a href="{decline_url}" class="btn-decline">❌ Decline</a>
            </div>
            <div class="warning">
                ⚠️ If you did not expect this invitation, you can safely decline or ignore this email.
            </div>
            <div class="footer">
                <p>This is an automated message, please do not reply.</p>
                <p>&copy; 2026 DevDuel. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return subject, html_body


def team_invite_new_user_template(
    team_name: str,
    role: str,
    register_url: str,
    inviter_email: str,
    inviter_name: str | None,
    invitee_name: str | None,
) -> tuple[str, str]:
    """
    Invite email for a user who is not yet registered.

    Returns:
        tuple[str, str]: (subject, html_body)
    """
    subject = f"You've been invited to join {team_name} on DevDuel"
    role_label = "Bidding Strategist" if role == "BIDDING" else "Coding Solver"
    role_color = "#9b59b6" if role == "BIDDING" else "#27ae60"
    role_icon = "🧠" if role == "BIDDING" else "💻"

    # Greeting: use invitee name if provided, otherwise generic
    greeting = f"Hello {invitee_name}," if invitee_name else "Hello,"

    # Inviter line: use name if available, otherwise just email
    if inviter_name:
        inviter_line = f'<strong>{inviter_name}</strong> (<a href="mailto:{inviter_email}" style="color:#3498db;">{inviter_email}</a>)'
    else:
        inviter_line = f'<a href="mailto:{inviter_email}" style="color:#3498db;">{inviter_email}</a>'

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                   line-height:1.6; color:#333; max-width:600px; margin:0 auto; padding:20px; }}
            .container {{ background:#f9f9f9; border-radius:8px; padding:30px; border:1px solid #e0e0e0; }}
            .header {{ text-align:center; margin-bottom:30px; }}
            .inviter-box {{ background:#eaf4fb; border-radius:8px; padding:15px 20px; margin:15px 0;
                           border-left:4px solid #3498db; }}
            .team-box {{ background:#fff; border:2px solid #3498db; border-radius:8px;
                        padding:20px; text-align:center; margin:25px 0; }}
            .team-name {{ font-size:22px; font-weight:bold; color:#2c3e50; margin-bottom:10px; }}
            .role-badge {{ display:inline-block; background:{role_color}; color:white;
                          padding:6px 16px; border-radius:20px; font-size:14px; font-weight:bold; }}
            .steps {{ background:#eaf4fb; border-radius:8px; padding:20px; margin:20px 0; }}
            .btn-register {{ display:block; background:#3498db; color:white !important;
                            text-decoration:none; padding:16px 32px; border-radius:6px;
                            font-size:16px; font-weight:bold; text-align:center; margin:30px 0; }}
            .warning {{ background:#fff3cd; border-left:4px solid #ffc107;
                       padding:15px; margin:20px 0; border-radius:4px; font-size:13px; }}
            .footer {{ text-align:center; margin-top:30px; font-size:12px; color:#7f8c8d; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header"><h1>⚔️ DevDuel Team Invitation</h1></div>
            <p>{greeting}</p>
            <div class="inviter-box">
                📩 <strong>Invited by:</strong> {inviter_line}
            </div>
            <p>You have been invited to join a team on <strong>DevDuel</strong> — a competitive coding
               platform that combines live bidding with real-time problem solving.</p>
            <div class="team-box">
                <div class="team-name">🏆 {team_name}</div>
                <div style="color:#7f8c8d; font-size:14px; margin-top:8px;">Your assigned role</div>
                <div class="role-badge">{role_icon} {role_label}</div>
            </div>
            <div class="steps">
                <p><strong>How it works:</strong></p>
                <p>1️⃣ Click the button below to create your free account</p>
                <p>2️⃣ Your email is pre-filled — just set a username and password</p>
                <p>3️⃣ Verify your email via OTP</p>
                <p>4️⃣ You'll be automatically added to the team</p>
            </div>
            <a href="{register_url}" class="btn-register">🚀 Create Account &amp; Join Team</a>
            <p style="font-size:13px; color:#7f8c8d; text-align:center;">
                This invite expires in <strong>72 hours</strong>.
            </p>
            <div class="warning">
                ⚠️ If you did not expect this invitation, you can safely ignore this email.
                No account will be created without your action.
            </div>
            <div class="footer">
                <p>This is an automated message, please do not reply.</p>
                <p>&copy; 2026 DevDuel. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return subject, html_body
