from django.utils.translation import gettext as _
from social_core.backends.facebook import FacebookOAuth2


class Facebook(FacebookOAuth2):
    persistent_session_warning = _(
        "Please note that you are still logged in to Facebook"
    )
    persistent_session_suggestion = _(
        "Go back to Facebook where you can log yourself out "
        "in the usual manner:"
    )
    persistent_session_link = _(
        "Go to Facebook"
    )
    persistent_session_final_warning = _(
        "If access to this device is shared by other users, "
        "the next user will be able to access your Facebook account "
        "unless you explicitly log out from Facebook."
    )
    user_facing_url = 'https://www.facebook.com'
