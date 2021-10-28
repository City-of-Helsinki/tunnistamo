from functools import lru_cache

from django.utils.translation import gettext, pgettext
from requests import RequestException
from social_core.backends.azuread_tenant import AzureADTenantOAuth2
from social_core.exceptions import AuthFailed


class HelsinkiAzureADTenantOAuth2(AzureADTenantOAuth2):
    name = 'helsinkiazuread'
    name_baseform = gettext('Azure AD')
    name_access = pgettext('access to []', 'Azure AD')
    name_genetive = pgettext('genetive form', 'Azure AD\'s')
    name_logged_in_to = pgettext('logged in to []', 'Azure AD')
    name_logout_from = pgettext('log out from []', 'Azure AD')
    name_goto = pgettext('go to []', 'Azure AD')

    @property
    @lru_cache()
    def LOGOUT_URL(self):  # noqa
        try:
            resp = self.request(self.openid_configuration_url(), method='GET')
            return resp.json().get('end_session_endpoint')
        except (AuthFailed, RequestException):
            return None

    def get_user_details(self, response):
        details = super().get_user_details(response)
        details['ad_groups'] = response.get('groups')
        details['onprem_sid'] = response.get('onprem_sid')

        return details

    def extra_data(self, user, uid, response, details=None, *args, **kwargs):
        """Add onprem_sid to the extra_data

        It can be used to match on-prem AD and Azure AD users later"""
        data = super().extra_data(user, uid, response, details, *args, **kwargs)
        data['onprem_sid'] = response.get('onprem_sid')

        return data
