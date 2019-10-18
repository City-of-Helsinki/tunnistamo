#!/bin/bash

set -e

until nc -z -v -w30 "$DATABASE_HOST" 5432
do
  echo "Waiting for postgres database connection..."
  sleep 1
done
echo "Database is up!"


# Apply database migrations
if [[ "$APPLY_MIGRATIONS" = "1" ]]; then
    echo "Applying database migrations..."
    ./manage.py migrate --noinput
fi

if [[ "$SETUP_DEV_OIDC" = "1" ]]; then
    echo "Setting up a OIDC test environments"
    ./manage.py add_oidc_client \
      --confidential \
      --name Profiles \
      --response_types "id_token token" \
      --redirect_uris https://oidcdebugger.com/debug \
      --client_id https://api.hel.fi/auth/profiles \
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
      --scopes "https://api.hel.fi/auth/profiles login_entries consents email profile"

    ./manage.py add_oidc_api \
      --name profiles \
      --domain https://api.hel.fi/auth \
      --scopes profile email \
      --client_id https://api.hel.fi/auth/profiles

    ./manage.py add_oidc_api_scope \
      --name Profiles \
      --api_name profiles \
      --description "Profile backend" \
      --client_ids https://api.hel.fi/auth/profiles

    echo "The following test OIDC environments are available:

  # PROFILE CLIENT & API
  Client id      : https://api.hel.fi/auth/profiles
  Response types : id_token token
  Login methods  : GitHub
  Redirect URLs  : https://oidcdebugger.com/debug
  API Scope      : profile, email

  # PROJECT CLIENT
  Client id      : http://tunnistamo-backend:8000/project (please add 'tunnistamo-backend' to your hosts file)
  Response types : code
  Login methods  : GitHub, Google, Yle Tunnus
  Redirect URLs  : http://localhost:8000/complete/tunnistamo/ & https://oidcdebugger.com/debug
  Scopes: https://api.hel.fi/auth/profiles login_entries consents email profile

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
    uwsgi --ini .prod/uwsgi.ini
fi
