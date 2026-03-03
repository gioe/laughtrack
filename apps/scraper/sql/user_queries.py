class UserQueries:

    GET_USERS_FROM_EMAILS = """
    SELECT id, email, name FROM users WHERE email = %s
    """

    GET_NOTIFIABLE_USERS = """
    SELECT u.id, u.email, u.name
    FROM users u
    JOIN user_profiles up ON u.id = up.user_id
    WHERE up.email_show_notifications = true
    """