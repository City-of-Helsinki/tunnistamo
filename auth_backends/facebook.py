from django.utils.translation import gettext, pgettext
from social_core.backends.facebook import FacebookOAuth2


class Facebook(FacebookOAuth2):
    user_facing_url = 'https://www.facebook.com'
    name_baseform = gettext('Facebook')
    name_access = pgettext('access to []', 'Facebook')
    name_genetive = pgettext('genetive form', 'Facebook')
    name_logged_in_to = pgettext('logged in to []', 'Facebook')
    name_logout_from = pgettext('log out from []', 'Facebook')
    name_goto = pgettext('go to []', 'Facebook')
