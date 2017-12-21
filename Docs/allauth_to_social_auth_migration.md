Django All Auth to Django Social Auth migration
============================================

Steps to migrate a Tunnistamo deployment to the social auth:
- Install new requirements
- Add `social_django` to `INSTALLED_APPS`
- Add social auth authentication backends to the `AUTHENTICATION_BACKENDS` setting. e.g.

```
AUTHENTICATION_BACKENDS = (
    'adfs_backend.helsinki.HelsinkiADFS',
    'adfs_backend.espoo.EspooADFS',
    'social_core.backends.facebook.FacebookOAuth2',
    'tunnistamo.backends.GoogleOAuth2CustomName',
    'social_core.backends.github.GithubOAuth2',
    ...
)
```

- Configure social auth pipeline in settings. e.g.

```
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'users.pipeline.get_user_uuid',
    'users.pipeline.get_username',
    'users.pipeline.require_email',
    'users.pipeline.deny_duplicate_email',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
    'users.pipeline.update_ad_groups',
)
```

- Add keys, secrets, and settings for each of the backends in use. e.g.

```
SOCIAL_AUTH_ADMIN_USER_SEARCH_FIELDS = ['email', 'first_name', 'last_name']

SOCIAL_AUTH_FACEBOOK_KEY = ''
SOCIAL_AUTH_FACEBOOK_SECRET = ''
SOCIAL_AUTH_FACEBOOK_SCOPE = ['email', 'public_profile']
# Request that Facebook includes email address in the returned details
SOCIAL_AUTH_FACEBOOK_PROFILE_EXTRA_PARAMS = {
    'fields': 'id,name,email',
}
# Allow setting the auth_type in GET parameters
SOCIAL_AUTH_FACEBOOK_AUTH_EXTRA_ARGUMENTS = {'auth_type': ''}

SOCIAL_AUTH_GITHUB_KEY = ''
SOCIAL_AUTH_GITHUB_SECRET = ''

SOCIAL_AUTH_GOOGLE_KEY = ''
SOCIAL_AUTH_GOOGLE_SECRET = ''
SOCIAL_AUTH_GOOGLE_SCOPE = ['email']

SOCIAL_AUTH_HELSINKI_ADFS_KEY = ''
SOCIAL_AUTH_HELSINKI_ADFS_SECRET = None

SOCIAL_AUTH_ESPOO_ADFS_KEY = ''
SOCIAL_AUTH_ESPOO_ADFS_SECRET = ''
```

- Run the `social_auth_migrate` migration command

The command will copy the existing allauth `SocialAccount` entries to social auth `UserSocialAuth` entries.

## Notes

- Google authentication backend is customized to change the default name to match the one used with allauth. (`google-oauth2` -> `google`)

## Custom authentication pipeline functions:

### users.pipeline.get_user_uuid

Makes sure that a `new_uuid` argument is available to other pipeline entries.

If the backend provides `get_user_uuid` method (as is the case with the ADFS backends), it is used to generate the UUID. Otherwise, the UUID is generated with `uuid.uuid1` function.

### users.pipeline.get_username

Sets the username argument. If the user exists already, use the existing username. Otherwise generate username from the `new_uuid` using the `helusers.utils.uuid_to_username` function.

### users.pipeline.require_email

Stop authentication and redirect to the `email_needed`view if the `details` received from the social auth doesn't include an email address.

### users.pipeline.deny_duplicate_email

Stop authentication if the email address already exists in the user database and the user has authenticated through one of the social logins. If the email exists in one of the users, but the user has only authenticated using password, connect the social login with the user.

### users.pipeline.update_ad_groups

Updates the users `ADGroup`s if the user authenticated through an ADFS backend.

TODO
====

- [ ] Test Espoo ADFS back
- [ ] Test YleTunnus backend
- [ ] Tests for the custom social pipeline
- [ ] More tests for the backends
- [ ] Remove allauth
- [ ] Remove adfs_provider package
- [ ] Implement connection of additional backends to an existing user
- [ ] If the login is for an app or OIDC Connect Client, make sure that the used backend is an allowed login method.
- [ ] Convert Suomi.fi allauth provider to a social auth backend
