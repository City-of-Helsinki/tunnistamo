ID Token
========

Contents of the token
---------------------

ID Token should look like this:

.. code-block:: javascript

  {
      "iss": "https://oma.hel.fi",
      "auth_time": 1483885641,
      "iat": 1483885643,
      "exp": 1483886243,
      "aud": [
          "https://api.hel.fi/auth/kerrokantasi-ui",
          "https://api.hel.fi/auth/kerrokantasi",
          "https://api.hel.fi/auth/respa"
      ],
      "azp": "https://api.hel.fi/auth/kerrokantasi-ui",
      "at_hash": "aU0XRQdbGq6IEth0z5dppg",
      "nonce": "kze88m"
      "https://api.hel.fi/auth": [
          "kerrokantasi",
          "respa.readonly",
      ],
      "sub": "33e0b08a-b7e3-11e6-b1d7-f0761c0512c2",
      "name": "Tuomas Suutari",
      "nickname": "Tuomas",
      "given_name": "Tuomas",
      "family_name": "Suutari",
      "github_username": "suutari-ai",
      "email": "tuomas.suutari@gmail.com",
      "email_verified": true,
  }


Things to note from that:

* ``aud`` contains a list of audiences, the first in the list is the
  client ID of the OIDC client requesting the token (usually an UI
  app) and the rest are the audiences of the backend APIs.  Backend
  APIs should check that their audience identifier is listed there.

* ``azp`` (Authorized Party) contains the OIDC client's ID

* Authorized API scopes are listed in claim named by the "API domain",
  in the example this is ``https://api.hel.fi/auth``.  API domains are
  stored into the database and can be managed in Django Admin.  API
  backend may use this claim to fine tune the permissions.

API scopes
----------

The API scopes are similar to `Google's API scopes
<https://developers.google.com/identity/protocols/googlescopes>`_ and
may look like this:

+--------------------------------------+-----------------------------------+
|Scope                                 |Description                        |
+======================================+===================================+
|https://api.hel.fi/auth/kerrokantasi  |View and manage your data in       |
|                                      |Kerrokantasi service               |
+--------------------------------------+-----------------------------------+
|https://api.hel.fi/auth/respa         |View and manage your reservations  |
|                                      |in Varaamo                         |
+--------------------------------------+-----------------------------------+
|https://api.hel.fi/auth/respa.readonly|View your reservations in Varaamo  |
+--------------------------------------+-----------------------------------+

Requesting API access
---------------------

Authorization for the scopes is requested in OIDC scope parameter, e.g.
``scope="openid https://api.hel.fi/auth/kerrokantasi"``.  Each API scope
might depend on additional OIDC scopes (e.g. ``profile``, ``email``, or
``github_username``) and those will be added automatically so that:

* If user consent is requested, the automatically included scopes are
  also listed in the "consent screen".

* Claims data from the automatically added scopes is also included to
  the ID Token.
