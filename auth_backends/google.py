from django.utils.translation import gettext as _
from social_core.backends.google import GoogleOAuth2


class GoogleOAuth2CustomName(GoogleOAuth2):
    name = 'google'

    persistent_session_warning = _(
        "Please note that you are still logged in to Google's services"
    )
    persistent_session_suggestion = _(
        "Go back to Google to log yourself out "
        "in the usual manner:"
    )
    persistent_session_link = _(
        "Go to Google"
    )
    persistent_session_final_warning = _(
        "If access to this device is shared by other users, "
        "the next user will be able to access your Google account "
        "unless you explicitly log out from Google."
    )
    user_facing_url = 'https://myaccount.google.com/'
