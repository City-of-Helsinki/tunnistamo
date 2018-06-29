"""
Django settings for tunnistamo project.

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

    'parler',
    'sass_processor',

    'oauth2_provider',
    'users',
    'oidc_provider',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.github',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.tumblr',

    'social_django',

    'rest_framework',
    'corsheaders',
    'helsinki_theme',
    'bootstrap3',
    'crequest',

    'helusers',

    'yletunnus',
    'adfs_provider',
    'hkijwt',
    'oidc_apis',
    'devices',
    'identities',
    'services',
)

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'crequest.middleware.CrequestMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'auth_backends.adfs.helsinki.HelsinkiADFS',
    'auth_backends.adfs.espoo.EspooADFS',
    'auth_backends.google.GoogleOAuth2CustomName',
    'yletunnus.backends.YleTunnusOAuth2',
    'social_core.backends.facebook.FacebookOAuth2',
    'social_core.backends.github.GithubOAuth2',
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

ROOT_URLCONF = 'tunnistamo.urls'

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
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
        },
    },
]

WSGI_APPLICATION = 'tunnistamo.wsgi.application'

#
# Database
#
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'tunnistamo',
    }
}

#
# Internationalization
#
LANGUAGE_CODE = 'fi'

LANGUAGES = (
    ('fi', 'Finnish'),
    ('en', 'English'),
    ('sv', 'Swedish')
)

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/profile/'

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
AUTH_USER_MODEL = 'users.User'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'npm.finders.NpmFinder',
    'sass_processor.finders.CssFinder',
)

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/sso/static/'

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

STATICFILES_DIRS = [
    ('node_modules', os.path.join(BASE_DIR, 'node_modules')),
]

SITE_ID = 1

PARLER_LANGUAGES = {SITE_ID: [{'code': code} for (code, name) in LANGUAGES]}

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
            'class': 'logging.NullHandler',
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
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
    ),
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}
CSRF_COOKIE_NAME = 'sso-csrftoken'
SESSION_COOKIE_NAME = 'sso-sessionid'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_SCHEME', 'https')

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_AUTHENTICATION_METHOD = 'email'

SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_ENABLED = True
ACCOUNT_LOGOUT_ON_GET = True
SOCIALACCOUNT_ADAPTER = 'users.adapter.SocialAccountAdapter'
ACCOUNT_UNIQUE_EMAIL = True

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

# django-oidc-provider settings for OpenID Connect support
OIDC_USERINFO = 'tunnistamo.oidc.get_userinfo'
OIDC_IDTOKEN_SUB_GENERATOR = 'tunnistamo.oidc.sub_generator'
OIDC_EXTRA_SCOPE_CLAIMS = 'oidc_apis.scopes.CombinedScopeClaims'
OIDC_IDTOKEN_PROCESSING_HOOK = 'oidc_apis.id_token.process_id_token'
OIDC_AFTER_USERLOGIN_HOOK = 'oidc_apis.utils.after_userlogin_hook'

SASS_PROCESSOR_INCLUDE_DIRS = [
    os.path.join(BASE_DIR, 'node_modules'),
]

SASS_PRECISION = 8

TEST_NON_SERIALIZED_APPS = ['adfs_provider']

# Social Auth
SOCIAL_AUTH_PIPELINE = (
    # Get the information we can about the user and return it in a simple
    # format to create the user instance later. On some cases the details are
    # already part of the auth response from the provider, but sometimes this
    # could hit a provider API.
    'social_core.pipeline.social_auth.social_details',

    # Get the social uid from whichever service we're authing thru. The uid is
    # the unique identifier of the given user in the provider.
    'social_core.pipeline.social_auth.social_uid',

    # Verifies that the current auth process is valid within the current
    # project, this is where emails and domains whitelists are applied (if
    # defined).
    'social_core.pipeline.social_auth.auth_allowed',

    # Checks if the current social-account is already associated in the site.
    'social_core.pipeline.social_auth.social_user',

    # Add `new_uuid` argument to the pipeline.
    'users.pipeline.get_user_uuid',
    # Sets the `username` argument.
    'users.pipeline.get_username',
    # Enforce email address.
    'users.pipeline.require_email',
    # Deny duplicate email or associate to an existing user by email
    'users.pipeline.associate_by_email',

    # Make up a username for this person, appends a random string at the end if
    # there's any collision.
    # 'social_core.pipeline.user.get_username',

    # Send a validation email to the user to verify its email address.
    # 'social_core.pipeline.mail.mail_validation',

    # Associates the current social details with another user account with
    # a similar email address.
    # 'social_core.pipeline.social_auth.associate_by_email',

    # Create a user account if we haven't found one yet.
    'social_core.pipeline.user.create_user',

    # Create the record that associated the social account with this user.
    'social_core.pipeline.social_auth.associate_user',

    # Populate the extra_data field in the social record with the values
    # specified by settings (and the default ones like access_token, etc).
    'social_core.pipeline.social_auth.load_extra_data',

    # Update the user record with any changed info from the auth service.
    'social_core.pipeline.user.user_details',

    # Update AD groups
    'users.pipeline.update_ad_groups',
)

SOCIAL_AUTH_ADMIN_USER_SEARCH_FIELDS = ['email', 'first_name', 'last_name']

SOCIAL_AUTH_FACEBOOK_KEY = ''
SOCIAL_AUTH_FACEBOOK_SECRET = ''
SOCIAL_AUTH_FACEBOOK_SCOPE = ['email', 'public_profile']
# Request that Facebook includes email address in the returned details
SOCIAL_AUTH_FACEBOOK_PROFILE_EXTRA_PARAMS = {
    'fields': 'id,name,email',
}
# Allow setting the auth_type in GET parameters
SOCIAL_AUTH_FACEBOOK_AUTH_EXTRA_ARGUMENTS = {'auth_type': ''}

SOCIAL_AUTH_GITHUB_KEY = ''
SOCIAL_AUTH_GITHUB_SECRET = ''

SOCIAL_AUTH_GOOGLE_KEY = ''
SOCIAL_AUTH_GOOGLE_SECRET = ''
SOCIAL_AUTH_GOOGLE_SCOPE = ['email']

SOCIAL_AUTH_HELSINKI_ADFS_KEY = ''
SOCIAL_AUTH_HELSINKI_ADFS_SECRET = None

SOCIAL_AUTH_ESPOO_ADFS_KEY = ''
SOCIAL_AUTH_ESPOO_ADFS_SECRET = None


# local_settings.py can be used to override environment-specific settings
# like database and email that differ between development and production.
local_settings_path = os.path.join(BASE_DIR, "local_settings.py")
if os.path.exists(local_settings_path):
    import sys
    import types
    module_name = "%s.local_settings" % ROOT_URLCONF.split('.')[0]
    module = types.ModuleType(module_name)
    module.__file__ = local_settings_path
    sys.modules[module_name] = module
    with open(local_settings_path, "rb") as f:
        exec(f.read())

if 'SECRET_KEY' not in locals():
    secret_file = os.path.join(BASE_DIR, '.django_secret')
    try:
        with open(secret_file) as f:
            SECRET_KEY = f.read().strip()
    except IOError:
        import random
        system_random = random.SystemRandom()
        try:
            SECRET_KEY = ''.join(
                [system_random.choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(64)])
            with open(secret_file, 'w') as f:
                import os
                os.fchmod(f.fileno(), 0o0600)
                f.write(SECRET_KEY)
                f.close()
        except IOError:
            Exception('Please create a %s file with random characters to generate your secret key!' % secret_file)
