import logging
from functools import lru_cache
from json import JSONDecodeError

from django.utils.translation import gettext, pgettext
from requests import RequestException
from social_core.backends.azuread_tenant import AzureADV2TenantOAuth2
from social_core.exceptions import AuthFailed

logger = logging.getLogger(__name__)


class HelsinkiAzureADTenantOAuth2(AzureADV2TenantOAuth2):
    name = 'helsinkiazuread'
    name_baseform = gettext('Azure AD')
    name_access = pgettext('access to []', 'Azure AD')
    name_genetive = pgettext('genetive form', 'Azure AD\'s')
    name_logged_in_to = pgettext('logged in to []', 'Azure AD')
    name_logout_from = pgettext('log out from []', 'Azure AD')
    name_goto = pgettext('go to []', 'Azure AD')
    USER_DATA_URL = 'https://graph.microsoft.com/v1.0/me/memberOf?$select=id,displayName,securityEnabled'

    @property
    @lru_cache()
    def LOGOUT_URL(self):  # noqa
        try:
            resp = self.request(self.openid_configuration_url(), method='GET')
            return resp.json().get('end_session_endpoint')
        except (AuthFailed, RequestException):
            return None

    def user_data(self, access_token, *args, **kwargs):
        """Read user data from the id_token and fetch groups from the Microsoft Graph

        The graph endpoint used is 'memberOf' instead of 'transitiveMemberOf'
        because the transitive groups should not be used in the services.

        Additionally, the groups that are not 'security groups' are filtered out for the
        same reason. The securityEnabled flag is checked in Python because the graph
        endpoint doesn't support this filter: '$filter=(securityEnabled eq true)' """
        user_data = super().user_data(access_token, *args, **kwargs)

        try:
            result = self.request(
                self.USER_DATA_URL,
                headers={
                    'Authorization': 'Bearer {0}'.format(access_token)
                }
            ).json()

            user_data['groups'] = [
                entry.get('displayName')
                for entry in result.get('value', [])
                if entry.get('securityEnabled')
            ]
        except (RequestException, JSONDecodeError, AttributeError) as e:
            # Just ignore the error if the request fails and use the groups already
            # possibly existing in the user_data
            logger.debug(
                'Failed to request user data from the Microsoft Graph:',
                exc_info=e
            )

        return user_data

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
