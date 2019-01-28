from django.conf import settings


class DefaultSettings(object):

    @property
    def KEY_MANAGER_RSA_KEY_LENGTH(self):
        """
        OPTIONAL. Length of the generated RSA key. Default value is 4096 bits.
        """
        return 4096

    @property
    def KEY_MANAGER_RSA_KEY_MAX_AGE(self):
        """
        OPTIONAL. Maximum lifetime of an RSA key. Default value is 90 days.
        """
        return 90

    @property
    def KEY_MANAGER_RSA_KEY_EXPIRATION_PERIOD(self):
        """
        OPTIONAL. Expiration period of an RSA key. Default value is 7 days.
        """
        return 7


default_settings = DefaultSettings()


def get(name):
    return getattr(settings, name, getattr(default_settings, name))
