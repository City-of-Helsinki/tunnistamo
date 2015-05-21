from djangosaml2.backends import Saml2Backend
import logging

logger = logging.getLogger(__name__)


class HelsinkiBackend(Saml2Backend):
    def _clean_attributes(self, session_info):
        attrs = session_info['ava']
        for attr in ('organizationName', 'emailAddress',
                     'windowsAccountName'):
            if attr not in attrs:
                continue
            attrs[attr][0] = attrs[attr][0].lower()
        if 'displayName' in attrs:
            names = attrs['displayName'][0].split(' ')
            attrs['lastName'] = [names[0]]
            attrs['firstName'] = [' '.join(names[1:])]

    def authenticate(self, session_info=None, attribute_mapping=None,
                     create_unknown_user=True):
        if session_info:
            self._clean_attributes(session_info)
        return super(HelsinkiBackend, self).authenticate(session_info, attribute_mapping,
                                                         create_unknown_user)
