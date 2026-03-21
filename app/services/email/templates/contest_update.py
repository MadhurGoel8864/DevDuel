"""Contest update notification email template."""

from datetime import datetime


def _format_value(value) -> str:
    """Format a field value for display in the email."""
    if isinstance(value, datetime):
        return value.strftime("%b %d, %Y %I:%M %p UTC")
    if value is None:
        return "—"
    return str(value)


def contest_update_template(
    contest_name: str,
    diff: dict[str, dict[str, object]],
) -> tuple[str, str]:
    """
    Generate a contest update notification email.

    Args:
        contest_name: Name of the contest (use new name if it changed).
        diff: Dict of changed fields in format:
              { "field_name": { "old": old_value, "new": new_value } }
              Only changed fields are included.

    Returns:
        Tuple of (subject, html_body).
    """
    subject = f"Contest Update: {contest_name}"

    # Build the changes table rows
    field_labels = {
        "name": "Contest Name",
        "description": "Description",
        "start_time": "Start Time",
        "end_time": "End Time",
    }

    rows_html = ""
    for field, values in diff.items():
        label = field_labels.get(field, field.replace("_", " ").title())
        old_val = _format_value(values["old"])
        new_val = _format_value(values["new"])
        rows_html += f"""
        <tr>
            <td style="padding: 10px 14px; border-bottom: 1px solid #e5e7eb;
                       font-weight: 500; color: #374151;">{label}</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #e5e7eb;
                       color: #6b7280; text-decoration: line-through;">{old_val}</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #e5e7eb;
                       color: #059669; font-weight: 500;">{new_val}</td>
        </tr>
        """

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #f9fafb;
                 font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
        <div style="max-width: 600px; margin: 40px auto; background: #ffffff;
                    border-radius: 12px; overflow: hidden;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);">

            <!-- Header -->
            <div style="background: #1e293b; padding: 28px 32px;">
                <h1 style="margin: 0; color: #ffffff; font-size: 20px;
                           font-weight: 600; letter-spacing: -0.3px;">
                    DevDuel
                </h1>
            </div>

            <!-- Body -->
            <div style="padding: 32px;">
                <h2 style="margin: 0 0 8px; color: #111827; font-size: 18px;
                           font-weight: 600;">
                    Contest Details Updated
                </h2>
                <p style="margin: 0 0 24px; color: #6b7280; font-size: 14px;">
                    The following changes were made to
                    <strong style="color: #111827;">{contest_name}</strong>:
                </p>

                <!-- Changes Table -->
                <table style="width: 100%; border-collapse: collapse;
                              border: 1px solid #e5e7eb; border-radius: 8px;
                              overflow: hidden; font-size: 14px;">
                    <thead>
                        <tr style="background: #f3f4f6;">
                            <th style="padding: 10px 14px; text-align: left;
                                       color: #374151; font-weight: 600;
                                       border-bottom: 1px solid #e5e7eb;">Field</th>
                            <th style="padding: 10px 14px; text-align: left;
                                       color: #374151; font-weight: 600;
                                       border-bottom: 1px solid #e5e7eb;">Old Value</th>
                            <th style="padding: 10px 14px; text-align: left;
                                       color: #374151; font-weight: 600;
                                       border-bottom: 1px solid #e5e7eb;">New Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>

                <p style="margin: 24px 0 0; color: #9ca3af; font-size: 12px;">
                    You are receiving this email because you are a member of a team
                    registered for this contest.
                </p>
            </div>

            <!-- Footer -->
            <div style="padding: 20px 32px; background: #f9fafb;
                        border-top: 1px solid #e5e7eb;">
                <p style="margin: 0; color: #9ca3af; font-size: 12px;">
                    © DevDuel. All rights reserved.
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    return subject, html_body
