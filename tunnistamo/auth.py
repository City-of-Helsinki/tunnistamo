import logging
import uuid

from djangosaml2.backends import Saml2Backend

logger = logging.getLogger(__name__)

# FIXME: put into settings.py
domain_uuid = uuid.UUID('1c8974a1-1f86-41a0-85dd-94a643370621')


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

        if 'primarySID' in attrs:
            user_uuid = uuid.uuid5(domain_uuid, attrs['primarySID'][0]).hex
            attrs['uuid'] = [user_uuid]

    def authenticate(self, session_info=None, attribute_mapping=None,
                     create_unknown_user=True):
        if session_info:
            self._clean_attributes(session_info)
        return super(HelsinkiBackend, self).authenticate(session_info, attribute_mapping,
                                                         create_unknown_user)
