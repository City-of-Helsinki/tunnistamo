Tokens in Tunnistamo
====================

Issued token types
------------------

Tunnistamo acts as an OpenID Connect (OIDC) Identity Provider (IdP) and
provides the standard OIDC token types: *ID Token*, *Access Token* and
*Refresh Token*.  In addition there is a fourth token type: *API Token*.

The ID Token can be used to identify the user in the client application
(aka Relying Party, RP) and the Access Token is used for IdP
communication, e.g. to get User Info or API Tokens from the IdP.  The
Refresh Token, when issued, can be used to get a fresh Access Token to
replace an expired token.  See `OIDC Documentation`_ for details.

.. _OIDC Documentation: http://openid.net/specs/openid-connect-core-1_0.html

The API Token is used when communicating with an API (aka Resource
Server, RS).  This differentiates from the OAuth2 standard, which uses
the Access Token for RS communication.  API Tokens are used instead to
provide a different set of claims for each RS while still encoding those
claims directly to the token to allow the RS to use the token without
communicating with the IdP.

ID Token
--------

ID Token is a signed JWT token.  Its payload looks like this in
Tunnistamo:

.. code-block:: javascript

  {
      "iss": "https://tunnistamo.hel.fi",
      "aud": "https://api.hel.fi/auth/kerrokantasi-ui",
      "sub": "33e0b08a-b7e3-11e6-b1d7-f0761c0512c2",
      "auth_time": 1483885641,
      "iat": 1483885643,
      "exp": 1483886243,
      "at_hash": "aU0XRQdbGq6IEth0z5dppg",
      "nonce": "kze88m"
      "name": "Maija Meikäläinen",
      "nickname": "Maija",
      "given_name": "Maija",
      "family_name": "Meikäläinen",
      "github_username": "maija-meikku",
      "email": "maija.meikalainen@meikku.fi",
      "email_verified": true,
  }

Access Token
------------

In Tunnistamo Access Token is an opaque string.

API Token
---------

API Token is also a signed JWT token like the ID Token.  A single API
Token is used for a single API.

Note: Even though API token is a JWT, it should be considered opaque for
the RP: it should have no need to decode it.

The payload of an API Token may contain different set of claims for each
API.

Authorized API scopes are listed in claim named by the "API domain".
The API application may use this claim to fine tune the permissions.
Only the API scopes of the specific API are present.  These scopes are
stored into the database and can be managed in the Django Admin.

TODO: What if API application needs to access another API application?

TODO: Should the API tokens be encrypted with JWE?

TODO: Should we use pairwise "sub" for API tokens?

Here is a couple API Token examples.  Their API domain is
``https://api.hel.fi/auth``, which is therefore also the name of the
claim for the authorized API scopes:

.. code-block:: javascript

  {
      "aud": "https://api.hel.fi/auth/kerrokantasi",
      "iss": "https://tunnistamo.hel.fi",
      "sub": "33e0b08a-b7e3-11e6-b1d7-f0761c0512c2",
      "auth_time": 1483885641,
      "iat": 1483885643,
      "exp": 1483886243,
      "https://api.hel.fi/auth": ["kerrokantasi"],
      "email": "maija.meikalainen@meikku.fi",
      "email_verified": true
  }

and

.. code-block:: javascript

  {
      "aud": "https://api.hel.fi/auth/respa",
      "iss": "https://tunnistamo.hel.fi",
      "sub": "33e0b08a-b7e3-11e6-b1d7-f0761c0512c2",
      "auth_time": 1483885641,
      "iat": 1483885643,
      "exp": 1483886243,
      "https://api.hel.fi/auth": ["respa.readonly"],
      "github_username": "maija-meikku"
  }


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

Authorization for the standard OIDC scopes and the API scopes is
requested in the scope parameter of the OIDC authorization request, e.g.
``scope=openid profile https://api.hel.fi/auth/kerrokantasi``.

Each API has a set of OIDC scopes that should be added to its API Token,
e.g. ``profile``, ``email``, or ``github_username``.  When user consent
is requested as part of the authorization, the API scopes are also
listed in the "consent screen".

The scopes required by the APIs are NOT included to the ID Token by
default.  They are neither present in the User Info response.  Specify
those scopes explicitly in the scope parameter to include them also to
the ID Token and User Info.

Obtaining the API tokens
------------------------

After the RP has authorized itself to one or more API scopes via the
OIDC authorization request, it may fetch the API tokens from the API
tokens endpoint using the Access Token for authorization.  This is done
with a simple GET request with the Access Token given in the
Authorization header (as a Bearer token) or in a query string (similarly
to OIDC userinfo endpoint).  The API Token URL is

  https://tunnistamo.hel.fi/api-tokens/

The response is a JSON encoded dictionary with the API identifiers as
the keys and the API tokens as the values.
