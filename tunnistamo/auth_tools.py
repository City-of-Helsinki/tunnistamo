def filter_login_methods_by_provider_ids_string(login_methods, provider_ids):
    if not login_methods or not provider_ids:
        return login_methods

    provider_ids = [provider_id.strip() for provider_id in provider_ids.split(',')]

    result = [
        login_method
        for login_method in login_methods
        if login_method.provider_id in provider_ids
    ]

    return result if result else login_methods
