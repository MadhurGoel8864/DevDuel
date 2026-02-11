import re


def sanitize_username(username: str) -> str:
    """
    Clean and validate username format.

    Rules:
    - Convert to lowercase
    - Replace spaces and special chars with underscores
    - Remove consecutive underscores
    - Remove leading/trailing underscores
    - Limit to 50 characters

    Args:
        username: Raw username string

    Returns:
        Sanitized username string
    """
    # Convert to lowercase
    username = username.lower()

    # Replace spaces and special characters with underscores
    username = re.sub(r"[^a-z0-9_]", "_", username)

    # Remove consecutive underscores
    username = re.sub(r"_+", "_", username)

    # Remove leading/trailing underscores
    username = username.strip("_")

    # Limit to 50 characters (database constraint)
    username = username[:50]

    return username


def generate_username_from_email(email: str) -> str:
    """
    Extract base username from email address.

    Examples:
        john.doe@example.com -> john_doe
        user+tag@domain.com -> user
        test123@test.com -> test123

    Args:
        email: Email address

    Returns:
        Base username extracted from email
    """
    # Extract local part (before @)
    local_part = email.split("@")[0]

    # Remove plus addressing (e.g., user+tag -> user)
    local_part = local_part.split("+")[0]

    # Sanitize the username
    return sanitize_username(local_part)
