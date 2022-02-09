#!/bin/bash

set -e

if [ -z "$SKIP_DATABASE_CHECK" -o "$SKIP_DATABASE_CHECK" = "0" ]; then
  until nc -z -v -w30 "$DATABASE_HOST" 5432
  do
    echo "Waiting for postgres database connection..."
    sleep 1
  done
  echo "Database is up!"
fi

# Apply database migrations
if [[ "$APPLY_MIGRATIONS" = "1" ]]; then
    echo "Applying database migrations..."
    ./manage.py migrate --noinput
fi

if [[ "$SETUP_DEV_OIDC" = "1" ]]; then
    echo "Setting up a OIDC test environments"
    ./manage.py add_oidc_client \
      --confidential \
      --name Helsinkiprofile \
      --response_types "id_token token" \
      --redirect_uris https://oidcdebugger.com/debug \
      --client_id https://api.hel.fi/auth/helsinkiprofile \
      --site_type dev \
      --login_methods github

    ./manage.py add_oidc_client \
      --confidential \
      --name Project \
      --response_types code \
      --redirect_uris \
        http://localhost:8001/complete/tunnistamo/ \
        http://omahelsinki:8001/complete/tunnistamo/ \
        https://oidcdebugger.com/debug \
        http://tunnistamo-backend:8000/accounts/github/login/callback/ \
      --client_id http://tunnistamo-backend:8000/project \
      --site_type dev \
      --login_methods github \
      --scopes "https://api.hel.fi/auth/helsinkiprofile login_entries consents email profile"

    ./manage.py add_oidc_api \
      --name helsinkiprofile \
      --domain https://api.hel.fi/auth \
      --scopes profile email \
      --client_id https://api.hel.fi/auth/helsinkiprofile

    ./manage.py add_oidc_api_scope \
      --name Helsinkiprofile \
      --api_name helsinkiprofile \
      --description "Profile backend" \
      --client_ids https://api.hel.fi/auth/helsinkiprofile

    echo "The following test OIDC environments are available:

  # PROFILE CLIENT & API
  Client id      : https://api.hel.fi/auth/helsinkiprofile
  Response types : id_token token
  Login methods  : GitHub
  Redirect URLs  : https://oidcdebugger.com/debug
  API Scope      : profile, email

  # PROJECT CLIENT
  Client id      : http://tunnistamo-backend:8000/project (please add 'tunnistamo-backend' to your hosts file)
  Response types : code
  Login methods  : GitHub, Google, Yle Tunnus
  Redirect URLs  : http://localhost:8000/complete/tunnistamo/ & https://oidcdebugger.com/debug
  Scopes: https://api.hel.fi/auth/helsinkiprofile login_entries consents email profile

  To change the settings, please visit the admin panel and change
  the Client, API and API Scope accordingly.
"
fi


if [[ "$GENERATE_OPENID_KEY" = "1" ]]; then
    # (Re-)Generate OpenID RSA key if needed
    ./manage.py manage_openid_keys
fi

if [[ "$CREATE_SUPERUSER" = "1" ]]; then
    ./manage.py add_admin_user -u admin -p admin -e admin@example.com
    echo "Admin user created with credentials admin:admin (email: admin@example.com)"
fi

# Start server
if [[ ! -z "$@" ]]; then
    "$@"
elif [[ "$DEV_SERVER" = "1" ]]; then
    python ./manage.py runserver 0.0.0.0:8000
else
    # We want to have a *_URL environment variables configure
    # both Django static/media files URL generation
    # and the corresponding file serving in uWSGI.
    # uWSGI combines app mount path (in APP_URL_PATH) and static
    # map path (in *_URL). For Django we combine them here.

    # remove trailing slash for uWSGI URLs. uWSGI probably
    # does this by itself, but it does not hurt
    export STATIC_URL_ROOTLESS=$(readlink -m $STATIC_URL)
    export MEDIA_URL_ROOTLESS=$(readlink -m $MEDIA_URL)
    # Use readlink to remove double initial slashes in case of
    # APP_URL_PATH="/" and STATIC_URL="/static/". Also Django
    # needs the ending slash, which readlink removes
    STATIC_URL=$(readlink -m $APP_URL_PATH$STATIC_URL)/
    MEDIA_URL=$(readlink -m $APP_URL_PATH$MEDIA_URL)/
    uwsgi --ini .prod/uwsgi.ini
fi
