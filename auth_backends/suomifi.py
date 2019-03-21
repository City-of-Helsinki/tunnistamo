import json
import logging

from defusedxml.lxml import fromstring, tostring
from django.urls import reverse
from lxml import etree
from oidc_provider.models import Client
from social_core.backends.saml import SAMLAuth, SAMLIdentityProvider

from auth_backends.models import SuomiFiUserAttribute

NSMAP = {
    'alg': 'urn:oasis:names:tc:SAML:metadata:algsupport',
    'md': 'urn:oasis:names:tc:SAML:2.0:metadata',
    'mdattr': 'urn:oasis:names:tc:SAML:metadata:attribute',
    'mdui': 'urn:oasis:names:tc:SAML:metadata:ui',
    'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
    'xml': 'http://www.w3.org/XML/1998/namespace',
    'xs': 'http://www.w3.org/2001/XMLSchema',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
}

OID_USERID = 'urn:oid:1.2.246.21'


logger = logging.getLogger(__name__)


class SuomiFiSAMLIdentityProvider(SAMLIdentityProvider):
    """
    Suomi.fi compliant wrapper around SAML IdP configuration.

    Extends social_core.backends.saml.SAMLIdentityProvider by adding SLO
    configuration to IdP configuration data.
    """
    @property
    def logout_url(self):
        """str: SLO URL for this IdP"""
        return self.conf['logout_url']

    @property
    def saml_config_dict(self):
        """dict: SLO extended IdP configuration in the format required by python-saml"""
        config = super().saml_config_dict
        # Extend the configuration with SLO support
        config['singleLogoutService'] = {
            'url': self.logout_url,
            # python-saml only supports Redirect
            'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
        }
        return config


class SuomiFiSAMLAuth(SAMLAuth):
    """
    Backend that implements SAML 2.0 SP functionality required by Suomi.fi IdP.

    This class extends social_core.backends.saml.SAMLAuth by adding support for
    generating Suomi.fi compliant SP metadata XML and methods to handle SLO
    functionality.

    In addition to the settings required by SAMLAuth there are a number of new
    settings and extended settings required by Suomi.fi. All the settings with
    name format of SOCIAL_AUTH_SAML_* required by SAMLAuth need to be given
    with name format of SOCIAL_AUTH_SUOMIFI_*. The following settings have been
    extended with new fields:

    SOCIAL_AUTH_SUOMIFI_TECHNICAL_CONTACT = {
        'givenName': '',
        'surName': '',
        'emailAddress': '',
    }
    SOCIAL_AUTH_SUOMIFI_SUPPORT_CONTACT = {
        'givenName': '',
        'surName': '',
        'emailAddress': '',
    }
    SOCIAL_AUTH_SUOMIFI_ENABLED_IDPS = {
        'suomifi': {
            'entity_id': '',
            'url': '',
            'logout_url': '',
            'x509cert': '',
        }
    }

    The following settings are required to be set:

    SOCIAL_AUTH_SUOMIFI_ORG_INFO = {
        'fi': {'name': '', 'displayname': '', 'url': ''},
        'sv': {'name': '', 'displayname': '', 'url': ''},
        'en': {'name': '', 'displayname': '', 'url': ''}
    }
    SOCIAL_AUTH_SUOMIFI_SP_EXTRA = {
        'NameIDFormat': 'urn:oasis:names:tc:SAML:2.0:nameid-format:transient',
        'attributeConsumingService': {
            'serviceName': '',
            'requestedAttributes': [
                # list of Suomi.fi attributes following format:
                {'friendlyName': '', 'name': ''},
            ]
        },
    }
    SOCIAL_AUTH_SUOMIFI_SECURITY_CONFIG = {'authnRequestsSigned': True,
                                           'logoutRequestSigned': True,
                                           'wantAssertionsSigned': True}

    In addition the following new settings are required:

    SOCIAL_AUTH_SUOMIFI_ENTITY_ATTRIBUTES = [
        {
            'name': 'FinnishAuthMethod',
            'nameFormat': 'urn:oasis:names:tc:SAML:2.0:attrname-format:uri',
            'values': [
                'http://ftn.ficora.fi/2017/loa3',
                'http://eidas.europa.eu/LoA/high',
                'http://ftn.ficora.fi/2017/loa2',
                'http://eidas.europa.eu/LoA/substantial',
                'urn:oid:1.2.246.517.3002.110.5',
                'urn:oid:1.2.246.517.3002.110.6',
                # 'urn:oid:1.2.246.517.3002.110.999' # Test authentication service
            ]
        },
        {
            'friendlyName': 'VthVerificationRequired',
            'name': 'urn:oid:1.2.246.517.3003.111.3',
            'nameFormat': 'urn:oasis:names:tc:SAML:2.0:attrname-format:uri',
            'values': ['false']
        },
        {
            'friendlyName': 'SkipEndpointValidationWhenSigned',
            'name': 'urn:oid:1.2.246.517.3003.111.4',
            'nameFormat': 'urn:oasis:names:tc:SAML:2.0:attrname-format:uri',
            'values': ['true']
        },
        {
            'friendlyName': 'EidasSupport',
            'name': 'urn:oid:1.2.246.517.3003.111.14',
            'nameFormat': 'urn:oasis:names:tc:SAML:2.0:attrname-format:uri',
            'values': ['full']
        },
    ]
    SOCIAL_AUTH_SUOMIFI_UI_INFO = {
        'fi': {'DisplayName': '', 'Description': '', 'PrivacyStatementURL': ''},
        'sv': {'DisplayName': '', 'Description': '', 'PrivacyStatementURL': ''},
        'en': {'DisplayName': '', 'Description': '', 'PrivacyStatementURL': ''},
    }
    SOCIAL_AUTH_SUOMIFI_UI_LOGO = {'url': '', 'height': None, 'width': None}

    """
    name = 'suomifi'
    EXTRA_DATA = ['name_id']

    def get_idp(self, idp_name):
        """Given the name of an IdP, get a SuomiFiSAMLIdentityProvider instance.
        Overrides the base class method."""
        idp_config = self.setting('ENABLED_IDPS')[idp_name]
        return SuomiFiSAMLIdentityProvider(idp_name, **idp_config)

    def generate_saml_config(self, idp=None):
        """Generate the configuration required to instantiate OneLogin_Saml2_Auth.
        Extends the base class method with SLO information and authentication
        methods."""
        config = super().generate_saml_config(idp)
        config['sp']['assertionConsumerService']['url'] = self.strategy.absolute_uri(
                reverse('social:complete', args=('suomifi',)))
        config['sp']['singleLogoutService'] = {
            'url': self.strategy.absolute_uri(reverse('auth_backends:suomifi_logout_callback')),
            'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
        }
        for attribute in self.setting('ENTITY_ATTRIBUTES'):
            if attribute['name'] == 'FinnishAuthMethod':
                config["security"].update({'requestedAuthnContext': attribute['values']})
        return config

    def generate_metadata_xml(self):
        """Helper method to generate the SP metadata XML. Extends the base class
        metadata generation with extensions, elements and attributes required by
        the Suomi.fi IdP.

        Returns (metadata XML string, list of errors)
        """
        metadata, errors = super().generate_metadata_xml()

        metadata_xml = fromstring(metadata)
        self._amend_services(metadata_xml)
        self._amend_contacts(metadata_xml)
        self._add_entity_attributes_extension(metadata_xml)
        self._add_ui_info_extension(metadata_xml)
        metadata = tostring(metadata_xml, encoding='utf-8', xml_declaration=True)

        return metadata, errors

    def _amend_services(self, metadata_xml):
        """Amend metadata XML service sections with fields required by Suomi.fi.
        This includes setting isDefault attribute to AssertionConsumerService and
        AttributeConsumingService and adding ServiceName and ServiceDescription
        tags to AttributeConsumingService for different languages.
        """
        metadata_xml.find('*/md:AssertionConsumerService', NSMAP).set('isDefault', 'true')
        attribute_consumer = metadata_xml.find('*/md:AttributeConsumingService', NSMAP)
        attribute_consumer.remove(attribute_consumer.find('md:ServiceName', NSMAP))
        attribute_consumer.set('isDefault', 'true')
        for lang, langdata in self.setting('UI_INFO').items():
            name = etree.SubElement(attribute_consumer, '{%s}ServiceName' % NSMAP['md'])
            name.set('{%s}lang' % NSMAP['xml'], lang)
            name.text = langdata['DisplayName']
            description = etree.SubElement(attribute_consumer, '{%s}ServiceDescription' % NSMAP['md'])
            description.set('{%s}lang' % NSMAP['xml'], lang)
            description.text = langdata['Description']

    def _amend_contacts(self, metadata_xml):
        """Amend metadata XML contact information with surnames."""
        for contact in metadata_xml.findall('md:ContactPerson', NSMAP):
            if contact.get('contactType') == 'technical':
                surname = etree.SubElement(contact, '{%s}SurName' % NSMAP['md'])
                surname.text = self.setting('TECHNICAL_CONTACT')['surName']
            if contact.get('contactType') == 'support':
                surname = etree.SubElement(contact, '{%s}SurName' % NSMAP['md'])
                surname.text = self.setting('SUPPORT_CONTACT')['surName']

    def _add_entity_attributes_extension(self, metadata_xml):
        """Add Suomi.fi required EntityAttributes extensions to metadata XML"""
        extensions = metadata_xml.find('md:Extensions', NSMAP)
        if not extensions:
            extensions = etree.Element(
                    '{%s}Extensions' % NSMAP['md'],
                    nsmap={'alg': NSMAP['alg']})
            metadata_xml.insert(0, extensions)
        attributes = etree.SubElement(
                extensions,
                '{%s}EntityAttributes' % NSMAP['mdattr'],
                nsmap={'mdattr': NSMAP['mdattr']})
        for attribute in self.setting('ENTITY_ATTRIBUTES'):
            attribute_element = etree.SubElement(attributes, '{%s}Attribute' % NSMAP['saml'])
            if 'name' in attribute:
                attribute_element.set('Name', attribute['name'])
            if 'friendlyName' in attribute:
                attribute_element.set('FriendlyName', attribute['friendlyName'])
            if 'nameFormat' in attribute and attribute['nameFormat']:
                attribute_element.set('NameFormat', attribute['nameFormat'])
            if 'values' in attribute:
                for value in attribute['values']:
                    value_element = etree.SubElement(
                            attribute_element,
                            '{%s}AttributeValue' % NSMAP['saml'],
                            nsmap={'xs': NSMAP['xs'], 'xsi': NSMAP['xsi']})
                    value_element.text = value
                    value_element.set('{%s}type' % NSMAP['xsi'], 'xs:string')

    def _add_ui_info_extension(self, metadata_xml):
        """Add UIInfo extension to metadata XML SPSSODescriptor."""
        extensions = metadata_xml.find('md:SPSSODescriptor/md:Extensions', NSMAP)
        if not extensions:
            descriptor = metadata_xml.find('md:SPSSODescriptor', NSMAP)
            extensions = etree.Element('{%s}Extensions' % NSMAP['md'])
            descriptor.insert(0, extensions)
        ui_info = etree.SubElement(
                extensions,
                '{%s}UIInfo' % NSMAP['mdui'],
                nsmap={'mdui': NSMAP['mdui']})
        for lang, langdata in self.setting('UI_INFO').items():
            for parameter, value in langdata.items():
                param = etree.SubElement(ui_info, '{%s}%s' % (NSMAP['mdui'], parameter))
                param.set('{%s}lang' % NSMAP['xml'], lang)
                param.text = value
        logodata = self.setting('UI_LOGO')
        if logodata:
            logo = etree.SubElement(ui_info, '{%s}Logo' % NSMAP['mdui'])
            if 'url' in logodata:
                logo.text = logodata['url']
            if 'height' in logodata and logodata['height']:
                logo.set('height', logodata['height'])
            if 'width' in logodata and logodata['width']:
                logo.set('width', logodata['width'])

    def auth_url(self):
        """Get the URL to which we must redirect in order to authenticate the user.
        Extends the base class method by adding LG query parameter to return URL."""
        url = super().auth_url()
        # Tunnistamo doesn't support other languages at the moment
        url += '&LG=fi'
        return url

    def extra_data(self, user, uid, response, details=None, *args, **kwargs):
        """Return default extra data to store in extra_data field.
        Extends the base class method by including session index to extra_data."""
        data = super().extra_data(user, uid, response, details=details, *args, **kwargs)
        data['session_index'] = response.get('session_index')
        data['suomifi_attributes'] = self._extract_suomifi_attributes(response)
        return data

    def _extract_suomifi_attributes(self, response):
        attributes = {}
        for attribute in SuomiFiUserAttribute.objects.all():
            if attribute.uri in response.get('attributes'):
                attributes[attribute.friendly_name] = response.get('attributes')[attribute.uri][0]
        return attributes

    @staticmethod
    def create_return_token(client, index):
        """Returns a token encoding given client and index"""
        return json.dumps({'cli': client, 'idx': index})

    @staticmethod
    def parse_return_token(token):
        """Returns client and index associated with given token"""
        try:
            token_dict = json.loads(token)
            return token_dict.get('cli'), token_dict.get('idx')
        except (json.JSONDecodeError, KeyError):
            logger.info('Invalid return token: {}'.format(token))
            return None, None

    def create_logout_redirect(self, social_user, token=''):
        """Returns a SP initiated SLO redirect message for given user.
        Token is used for tracking state."""
        idp = self.get_idp('suomifi')
        auth = self._create_saml_auth(idp=idp)
        redirect = auth.logout(return_to=token,
                               nq=idp.entity_id,
                               name_id=social_user.extra_data['name_id'],
                               name_id_format='urn:oasis:names:tc:SAML:2.0:nameid-format:transient',
                               session_index=social_user.extra_data['session_index'])
        social_user.extra_data = {}
        social_user.save()
        return self.strategy.redirect(redirect)

    def process_logout_message(self):
        """Processes SLO SAML message. Returns next step redirect."""
        idp = self.get_idp('suomifi')
        auth = self._create_saml_auth(idp=idp)
        redirect = auth.process_slo()
        # we don't get redirect from SAML for SLO responses
        if not redirect:
            client_id, index = self.parse_return_token(self.data.get('RelayState'))
            try:
                client = Client.objects.get(client_id=client_id)
                redirect = client.post_logout_redirect_uris[index]
            except (Client.DoesNotExist, IndexError):
                logger.info('Could not deduce return URI, using default value: {}'.format(self.redirect_uri))
                redirect = self.redirect_uri
        return self.strategy.redirect(redirect)
