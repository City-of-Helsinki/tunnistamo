from django.utils.translation import gettext, pgettext
from social_core.backends.google import GoogleOAuth2


class GoogleOAuth2CustomName(GoogleOAuth2):
    name = 'google'
    user_facing_url = 'https://myaccount.google.com/'
    name_baseform = gettext('Google')
    name_access = pgettext('access to []', 'Google')
    name_genetive = pgettext('genetive form', 'Google')
    name_logged_in_to = pgettext('logged in to []', 'Google')
    name_logout_from = pgettext('log out from []', 'Google')
    name_goto = pgettext('go to []', 'Google')
