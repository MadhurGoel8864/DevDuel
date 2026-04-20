"""
Email templates for team join requests.

Two variants:
  - Leader notification — when a user requests to join their team
  - Requester acceptance — when the leader accepts the request
"""


def team_join_request_leader_template(
    leader_name: str | None,
    team_name: str,
    requester_name: str | None,
    requester_email: str,
    role: str,
    manage_url: str,
) -> tuple[str, str]:
    """
    Email sent to the team leader when a user requests to join their team.

    Returns:
        tuple[str, str]: (subject, html_body)
    """
    subject = f"New join request for {team_name}"
    role_label = "Bidding Strategist" if role == "BIDDING" else "Coding Solver"
    role_color = "#9b59b6" if role == "BIDDING" else "#27ae60"
    role_icon = "🧠" if role == "BIDDING" else "💻"

    greeting = f"Hello {leader_name}," if leader_name else "Hello,"

    if requester_name:
        requester_line = (
            f'<strong>{requester_name}</strong> '
            f'(<a href="mailto:{requester_email}" style="color:#3498db;">{requester_email}</a>)'
        )
    else:
        requester_line = (
            f'<a href="mailto:{requester_email}" style="color:#3498db;">{requester_email}</a>'
        )

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
            .requester-box {{ background:#eaf4fb; border-radius:8px; padding:15px 20px; margin:15px 0;
                              border-left:4px solid #3498db; }}
            .team-box {{ background:#fff; border:2px solid #3498db; border-radius:8px;
                         padding:20px; text-align:center; margin:25px 0; }}
            .team-name {{ font-size:22px; font-weight:bold; color:#2c3e50; margin-bottom:10px; }}
            .role-badge {{ display:inline-block; background:{role_color}; color:white;
                           padding:6px 16px; border-radius:20px; font-size:14px; font-weight:bold; }}
            .btn-review {{ display:inline-block; background:#3498db; color:white !important;
                           text-decoration:none; padding:14px 32px; border-radius:6px;
                           font-size:16px; font-weight:bold; margin:20px 0; }}
            .info {{ background:#fff3cd; border-left:4px solid #ffc107;
                     padding:15px; margin:20px 0; border-radius:4px; font-size:13px; }}
            .footer {{ text-align:center; margin-top:30px; font-size:12px; color:#7f8c8d; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header"><h1>⚔️ DevDuel Team Join Request</h1></div>
            <p>{greeting}</p>
            <div class="requester-box">
                📩 <strong>Requester:</strong> {requester_line}
            </div>
            <p>Someone has requested to join your team on <strong>DevDuel</strong>.</p>
            <div class="team-box">
                <div class="team-name">🏆 {team_name}</div>
                <div style="color:#7f8c8d; font-size:14px; margin-top:8px;">Requested role</div>
                <div class="role-badge">{role_icon} {role_label}</div>
            </div>
            <div style="text-align:center;">
                <a href="{manage_url}" class="btn-review">📋 Review Request</a>
            </div>
            <div class="info">
                ℹ️ Open the team page to accept or reject this request. Your decision is final.
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


def team_join_request_accepted_template(
    requester_name: str | None,
    team_name: str,
    role: str,
    team_url: str,
) -> tuple[str, str]:
    """
    Email sent to the requester when the leader accepts their join request.

    Returns:
        tuple[str, str]: (subject, html_body)
    """
    subject = f"You've joined {team_name} on DevDuel!"
    role_label = "Bidding Strategist" if role == "BIDDING" else "Coding Solver"
    role_color = "#9b59b6" if role == "BIDDING" else "#27ae60"
    role_icon = "🧠" if role == "BIDDING" else "💻"

    greeting = f"Hello {requester_name}," if requester_name else "Hello,"

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
            .team-box {{ background:#fff; border:2px solid #27ae60; border-radius:8px;
                         padding:20px; text-align:center; margin:25px 0; }}
            .team-name {{ font-size:22px; font-weight:bold; color:#2c3e50; margin-bottom:10px; }}
            .role-badge {{ display:inline-block; background:{role_color}; color:white;
                           padding:6px 16px; border-radius:20px; font-size:14px; font-weight:bold; }}
            .btn-open {{ display:inline-block; background:#27ae60; color:white !important;
                         text-decoration:none; padding:14px 32px; border-radius:6px;
                         font-size:16px; font-weight:bold; margin:20px 0; }}
            .info {{ background:#eaf4fb; border-left:4px solid #3498db;
                     padding:15px; margin:20px 0; border-radius:4px; font-size:13px; }}
            .footer {{ text-align:center; margin-top:30px; font-size:12px; color:#7f8c8d; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header"><h1>🎉 You're In!</h1></div>
            <p>{greeting}</p>
            <p>Great news — your request to join the team has been <strong>accepted</strong>.</p>
            <div class="team-box">
                <div class="team-name">🏆 {team_name}</div>
                <div style="color:#7f8c8d; font-size:14px; margin-top:8px;">Your role</div>
                <div class="role-badge">{role_icon} {role_label}</div>
            </div>
            <div style="text-align:center;">
                <a href="{team_url}" class="btn-open">🚀 Open Team</a>
            </div>
            <div class="info">
                ℹ️ Head to your team page to coordinate with your teammate and prepare for the next contest.
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
