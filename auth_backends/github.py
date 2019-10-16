from django.utils.translation import gettext as _
from social_core.backends.github import GithubOAuth2


class Github(GithubOAuth2):
    persistent_session_warning = _(
        "Please note that you are still logged in to GitHub"
    )
    persistent_session_suggestion = _(
        "Go back to GitHub where you can log yourself out "
        "in the usual manner:"
    )
    persistent_session_link = _(
        "Go to GitHub"
    )
    persistent_session_final_warning = _(
        "If access to this device is shared by other users, "
        "the next user will be able to access your GitHub account "
        "unless you explicitly log out from GitHub."
    )
    user_facing_url = 'https://github.com'
