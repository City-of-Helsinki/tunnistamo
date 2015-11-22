"""
Django settings for hkisaml project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

DEBUG = False

TEMPLATE_DEBUG = False

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sites',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',

    'oauth2_provider',
    'users',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.github',
    'allauth.socialaccount.providers.google',

    'rest_framework',
    'djangosaml2',
    'corsheaders',
    'bootstrap3',

    'helusers',
    'helusers.providers.yletunnus',

    'hkijwt',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'hkisaml.auth.HelsinkiBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

ROOT_URLCONF = 'hkisaml.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'hkisaml.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'hkisaml',
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'fi'

LANGUAGES = (
    ('fi', 'suomi'),
    ('en', 'English'),
    ('sv', 'svenska')
)


TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/profile/'

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
AUTH_USER_MODEL = 'users.User'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

STATIC_URL = '/sso/static/'

SITE_ID = 1


from os import path
import saml2
from saml2 import saml
BASEDIR = path.dirname(path.abspath(__file__))
SAML_ATTRIBUTE_MAPPING = {
    'uuid': ['uuid'],
    'emailAddress': ['email'],
    'displayName': ['full_name'],
    'firstName': ['first_name'],
    'lastName': ['last_name'],
    'windowsAccountName': ['username'],
    'organizationName': ['department_name'],
    'primarySID': ['primary_sid'],
}
SAML_DJANGO_USER_MAIN_ATTRIBUTE = 'uuid'

SAML_CONFIG = {
    # full path to the xmlsec1 binary programm
    'xmlsec_binary': '/usr/bin/xmlsec1',

    # your entity id, usually your subdomain plus the url to the metadata view
    'entityid': 'https://api.hel.fi/sso/saml2/metadata/',

    # directory with attribute mapping
    'attribute_map_dir': path.join(BASEDIR, 'attribute-maps'),

    # this block states what services we provide
    'service': {
        'sp': {
            'name': 'City of Helsinki Open Software Development SAML',
            'name_id_format': saml.NAMEID_FORMAT_UNSPECIFIED1,
            #'name_id_format': '',
            'allow_unsolicited': True,
            'endpoints': {
                # url and binding to the assetion consumer service view
                # do not change the binding or service name
                'assertion_consumer_service': [
                    ('https://api.hel.fi/sso/saml2/acs/', saml2.BINDING_HTTP_POST),
                ],
                # url and binding to the single logout service view
                # do not change the binding or service name
                'single_logout_service': [
                    ('https://api.hel.fi/sso/saml2/ls/', saml2.BINDING_HTTP_REDIRECT),
                    #('https://api.hel.fi/sso/saml2/ls/post', saml2.BINDING_HTTP_POST),
                ],
            },

            # attributes that this project need to identify a user
            'required_attributes': ['uid'],

            # attributes that may be useful to have but not required
            'optional_attributes': ['eduPersonAffiliation'],

            # in this section the list of IdPs we talk to are defined
            'idp': {
                # we do not need a WAYF service since there is
                # only an IdP defined here. This IdP should be
                # present in our metadata

                # the keys of this dictionary are entity ids
                'http://sts.hel.fi/adfs/services/trust': {
                    'single_sign_on_service': {
                        saml2.BINDING_HTTP_REDIRECT: 'https://sts.hel.fi/adfs/ls/',
                    },
                    'single_logout_service': {
                        saml2.BINDING_HTTP_REDIRECT: 'https://sts.hel.fi/adfs/ls/?wa=wsignoutcleanup1.0',
                    },
                },
            },
        },
    },

    # where the remote metadata is stored
    'metadata': {
        'local': [path.join(BASEDIR, 'remote_metadata.xml')],
    },

    # set to 1 to output debugging information
    'debug': 1,

    # certificate
    'key_file': path.join(BASEDIR, 'mycert.key'),  # private part
    'cert_file': path.join(BASEDIR, 'mycert.pem'),  # public part

    # own metadata settings
    'contact_person': [{
        'given_name': 'Juha',
        'sur_name': 'Yrjola',
        'company': 'City of Helsinki',
        'email_address': 'juha.yrjola@hel.fi',
        'contact_type': 'technical'
    }],
    # you can set multilanguage information here
    # 'organization': {
    #    'name': [('City of Helsinki', 'en'), ('Helsingin kaupunki', 'fi')],
    # },
    'valid_for': 24,  # how long is our metadata valid
}


LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(module)s %(asctime)s %(levelname)s %(message)s'
        },
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'django.utils.log.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'generic': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'requests': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'sorl.thumbnail': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        }
    }
}

CORS_ORIGIN_ALLOW_ALL = True

OAUTH2_PROVIDER_APPLICATION_MODEL = 'users.Application'
OAUTH2_PROVIDER = {
    'CLIENT_SECRET_GENERATOR_LENGTH': 96,
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'oauth2_provider.ext.rest_framework.OAuth2Authentication',
    )
}
CSRF_COOKIE_NAME = 'sso-csrftoken'
SESSION_COOKIE_NAME = 'sso-sessionid'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_SCHEME', 'https')

SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_ENABLED = True
ACCOUNT_LOGOUT_ON_GET = True
SOCIALACCOUNT_ADAPTER = 'users.adapter.SocialAccountAdapter'

SOCIALACCOUNT_PROVIDERS = {
    'facebook': {
        'SCOPE': ['email', 'public_profile'],
        'VERIFIED_EMAIL': True,
        'VERSION': 'v2.4'
    },
    'github': {
        'VERIFIED_EMAIL': True,
    },
    'google': {
        'SCOPE': ['email'],
        'VERIFIED_EMAIL': True,
    },
    'yletunnus': {
        'VERIFIED_EMAIL': True,
    },

}


# local_settings.py can be used to override environment-specific settings
# like database and email that differ between development and production.
f = os.path.join(BASE_DIR, "local_settings.py")
if os.path.exists(f):
    import sys
    import imp
    module_name = "%s.local_settings" % ROOT_URLCONF.split('.')[0]
    module = imp.new_module(module_name)
    module.__file__ = f
    sys.modules[module_name] = module
    exec(open(f, "rb").read())

if 'SECRET_KEY' not in locals():
    secret_file = os.path.join(BASE_DIR, '.django_secret')
    try:
        SECRET_KEY = open(secret_file).read().strip()
    except IOError:
        import random
        system_random = random.SystemRandom()
        try:
            SECRET_KEY = ''.join([system_random.choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(64)])
            secret = open(secret_file, 'w')
            import os
            os.chmod(secret_file, 0o0600)
            secret.write(SECRET_KEY)
            secret.close()
        except IOError:
            Exception('Please create a %s file with random characters to generate your secret key!' % secret_file)
