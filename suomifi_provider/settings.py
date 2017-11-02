from django.conf import settings as django_settings
from lxml import etree
from onelogin.saml2.constants import OneLogin_Saml2_Constants
from onelogin.saml2.errors import OneLogin_Saml2_Error
from onelogin.saml2.metadata import OneLogin_Saml2_Metadata
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.xml_utils import OneLogin_Saml2_XML

from suomifi_provider.suomifi_uri import MAP


class SuomiFi_Saml2_Settings(OneLogin_Saml2_Settings):
    NS_MD_ATTR = 'urn:oasis:names:tc:SAML:metadata:attribute'
    NS_MDUI = 'urn:oasis:names:tc:SAML:metadata:ui'

    def __init__(self, settings=None, custom_base_path=None, sp_validation_only=False):
        super().__init__(settings, custom_base_path, sp_validation_only)

        self.ui = settings['ui']
        self.service_name = settings['service_name']

    def check_settings(self, settings):
        errors = super().check_settings(settings)

        if 'ui' not in settings:
            errors.append('ui settings missing')

        if 'service_name' not in settings:
            errors.append('service_name setting missing')

        return errors

    def add_finnishauthmethod_extension(self, metadata):
        try:
            root = OneLogin_Saml2_XML.to_etree(metadata)
        except Exception as e:
            raise Exception('Error parsing metadata. ' + str(e))

        extensions = etree.Element('{%s}Extensions' % OneLogin_Saml2_Constants.NS_MD)
        root.insert(0, extensions)

        etree.register_namespace('mdattr', self.NS_MD_ATTR)
        etree.register_namespace('xs', OneLogin_Saml2_Constants.NS_XS)

        entity_attributes = OneLogin_Saml2_XML.make_child(extensions, etree.QName(self.NS_MD_ATTR, 'EntityAttributes'))
        attribute = OneLogin_Saml2_XML.make_child(entity_attributes, etree.QName(OneLogin_Saml2_Constants.NS_SAML,
                                                                                 'Attribute'))
        attribute.set('Name', 'FinnishAuthMethod')
        attribute.set('NameFormat', OneLogin_Saml2_Constants.ATTRNAME_FORMAT_URI)

        attribute_value_texts = [
            MAP['to']['verkkopankkitunnus'],
            MAP['to']['varmennekortti'],
            MAP['to']['mobiilivarmenne'],
            MAP['to']['KatsoOTP'],
            MAP['to']['KatsoPWD'],
        ]

        if django_settings.DEBUG:
            attribute_value_texts.append(MAP['to']['testitunnistusväline'])

        for attribute_value_text in attribute_value_texts:
            attribute_value = OneLogin_Saml2_XML.make_child(
                attribute,
                etree.QName(OneLogin_Saml2_Constants.NS_SAML, 'AttributeValue'),
            )
            attribute_value.set(
                etree.QName(OneLogin_Saml2_Constants.NS_XSI, 'type'),
                etree.QName(OneLogin_Saml2_Constants.NS_XS, 'string')
            )
            attribute_value.text = attribute_value_text

        return OneLogin_Saml2_XML.to_string(root)

    def fix_acs_service_name(self, metadata):
        try:
            root = OneLogin_Saml2_XML.to_etree(metadata)
        except Exception as e:
            raise Exception('Error parsing metadata. ' + str(e))

        try:
            acs_node = OneLogin_Saml2_XML.query(
                root, '/md:EntityDescriptor/md:SPSSODescriptor/md:AttributeConsumingService')[0]
        except IndexError:
            return OneLogin_Saml2_XML.to_string(root)

        try:
            service_name_node = OneLogin_Saml2_XML.query(root, 'md:ServiceName', acs_node)[0]
        except IndexError:
            return OneLogin_Saml2_XML.to_string(root)

        # service_name = service_name_node.text
        acs_node.remove(service_name_node)

        languages = [i[0] for i in django_settings.LANGUAGES]

        for lang in languages:
            new_name_node = etree.Element(etree.QName(OneLogin_Saml2_Constants.NS_MD, 'ServiceName'),
                                          attrib={"{http://www.w3.org/XML/1998/namespace}lang": lang})
            new_name_node.text = self.service_name.get(lang)
            acs_node.insert(0, new_name_node)

        return OneLogin_Saml2_XML.to_string(root)

    def add_mdui_tags(self, metadata):
        etree.register_namespace('mdui', self.NS_MDUI)

        try:
            root = OneLogin_Saml2_XML.to_etree(metadata)
        except Exception as e:
            raise Exception('Error parsing metadata. ' + str(e))

        try:
            sp_sso_descriptor_node = OneLogin_Saml2_XML.query(root, '/md:EntityDescriptor/md:SPSSODescriptor')[0]
        except IndexError:
            return OneLogin_Saml2_XML.to_string(root)

        extensions = etree.Element(etree.QName(OneLogin_Saml2_Constants.NS_MD, 'Extensions'))
        sp_sso_descriptor_node.insert(0, extensions)

        uiinfo = etree.SubElement(extensions, etree.QName(self.NS_MDUI, 'UIInfo'))

        languages = [i[0] for i in django_settings.LANGUAGES]

        for lang in languages:
            display_name_node = etree.SubElement(uiinfo, etree.QName(self.NS_MDUI, 'displayName'), attrib={
                "{http://www.w3.org/XML/1998/namespace}lang": lang
            })
            display_name_node.text = self.ui.get(lang, {}).get('displayname')

            description_node = etree.SubElement(uiinfo, etree.QName(self.NS_MDUI, 'Description'), attrib={
                "{http://www.w3.org/XML/1998/namespace}lang": lang
            })
            description_node.text = self.ui.get(lang, {}).get('description')

            privacy_node = etree.SubElement(uiinfo, etree.QName(self.NS_MDUI, 'PrivacyStatementURL'), attrib={
                "{http://www.w3.org/XML/1998/namespace}lang": lang
            })
            privacy_node.text = self.ui.get(lang, {}).get('privacy_statement_url')

        logo = etree.SubElement(uiinfo, etree.QName(self.NS_MDUI, 'Logo'), attrib={
            # "height": "0",
            # "width": "0",
        })
        logo.text = self.ui.get('logo')

        return OneLogin_Saml2_XML.to_string(root)

    def get_sp_metadata(self):
        """
        Gets the SP metadata. The XML representation.
        :returns: SP metadata (xml)
        :rtype: string
        """
        self.sp = self.get_sp_data()
        self.security = self.get_security_data()

        metadata = OneLogin_Saml2_Metadata.builder(
            self.sp,
            self.security['authnRequestsSigned'],
            self.security['wantAssertionsSigned'],
            self.security['metadataValidUntil'],
            self.security['metadataCacheDuration'],
            self.get_contacts(), self.get_organization()
        )

        add_encryption = self.security['wantNameIdEncrypted'] or self.security['wantAssertionsEncrypted']

        cert_new = self.get_sp_cert_new()
        metadata = OneLogin_Saml2_Metadata.add_x509_key_descriptors(metadata, cert_new, add_encryption)

        cert = self.get_sp_cert()
        metadata = OneLogin_Saml2_Metadata.add_x509_key_descriptors(metadata, cert, add_encryption)

        metadata = self.add_finnishauthmethod_extension(metadata)
        metadata = self.fix_acs_service_name(metadata)
        metadata = self.add_mdui_tags(metadata)

        # This is a kludge to add the xs namespace which is used in the FinnishAuthMethod AttributeValue.
        # (lxml strips "unused" namespaces)
        metadata = metadata.replace(rb'<md:EntityDescriptor ',
                                    rb'<md:EntityDescriptor xmlns:xs="http://www.w3.org/2001/XMLSchema" ')

        # Sign metadata
        if 'signMetadata' in self.security and self.security['signMetadata'] is not False:
            if self.security['signMetadata'] is True:
                # Use the SP's normal key to sign the metadata:
                if not cert:
                    raise OneLogin_Saml2_Error(
                        'Cannot sign metadata: missing SP public key certificate.',
                        OneLogin_Saml2_Error.PUBLIC_CERT_FILE_NOT_FOUND
                    )
                cert_metadata = cert
                key_metadata = self.get_sp_key()
                if not key_metadata:
                    raise OneLogin_Saml2_Error(
                        'Cannot sign metadata: missing SP private key.',
                        OneLogin_Saml2_Error.PRIVATE_KEY_FILE_NOT_FOUND
                    )
            else:
                # Use a custom key to sign the metadata:
                if ('keyFileName' not in self.security['signMetadata'] or
                        'certFileName' not in self.security['signMetadata']):
                    raise OneLogin_Saml2_Error(
                        'Invalid Setting: signMetadata value of the sp is not valid',
                        OneLogin_Saml2_Error.SETTINGS_INVALID_SYNTAX
                    )
                key_file_name = self.security['signMetadata']['keyFileName']
                cert_file_name = self.security['signMetadata']['certFileName']
                key_metadata_file = self.get_cert_path() + key_file_name
                cert_metadata_file = self.get_cert_path() + cert_file_name

                try:
                    with open(key_metadata_file, 'r') as f_metadata_key:
                        key_metadata = f_metadata_key.read()
                except IOError:
                    raise OneLogin_Saml2_Error(
                        'Private key file not readable: %s',
                        OneLogin_Saml2_Error.PRIVATE_KEY_FILE_NOT_FOUND,
                        key_metadata_file
                    )

                try:
                    with open(cert_metadata_file, 'r') as f_metadata_cert:
                        cert_metadata = f_metadata_cert.read()
                except IOError:
                    raise OneLogin_Saml2_Error(
                        'Public cert file not readable: %s',
                        OneLogin_Saml2_Error.PUBLIC_CERT_FILE_NOT_FOUND,
                        cert_metadata_file
                    )

            signature_algorithm = self.security['signatureAlgorithm']
            digest_algorithm = self.security['digestAlgorithm']

            metadata = OneLogin_Saml2_Metadata.sign_metadata(metadata, key_metadata, cert_metadata, signature_algorithm,
                                                             digest_algorithm)

        return metadata

