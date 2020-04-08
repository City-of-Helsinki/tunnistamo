from django.utils.translation import gettext, pgettext
from social_core.backends.github import GithubOAuth2


class Github(GithubOAuth2):
    user_facing_url = 'https://github.com'
    name_baseform = gettext('GitHub')
    name_access = pgettext('access to []', 'GitHub')
    name_genetive = pgettext('genetive form', 'GitHub')
    name_logged_in_to = pgettext('logged in to []', 'GitHub')
    name_logout_from = pgettext('log out from []', 'GitHub')
    name_goto = pgettext('go to []', 'GitHub')
