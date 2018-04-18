# Authenticating using user-controlled devices

Tunnistamo supports authenticating users through user-controlled devices. The only device we currently support is a mobile phone that has the [Open City App](https://github.com/City-of-Helsinki/open-city-app) installed.

## Login and registration

### Login

The user must be authenticated to Tunnistamo first. We support only browser-based login, so for native applications some kind of integrated browser (such as WebView) must be used.

After the user completes the login flow, an access token is provided to the application. The app must then generate an Elliptic Curve (EC) key pair on the NIST P-256 curve. The new device is then registered with a `POST` request to the `/v1/user_device/` endpoint.

```
POST <prefix>/v1/user_device/

Authentication: Bearer <access token>
```

```json
{
    "public_key": {
        "kty": "EC",
        "use": "sig",
        "crv": "P-256",
        "alg": "ES256",
        "x": "UdTokfffnUeczbK2-7QuBq_YaDgXek6IreqhGZ1cR4s",
        "y": "NBJKDLcZejGp1msCzHRNopykrEbktsqWsk4hGdr6gPk"
    },
    "os": "android",
    "os_version": "7.1",
    "app_version": "0.1.0",
    "device_model": "LG G5"
}
```

When Tunnistamo receives the request, it will generate a shared secret that is returned in the response to the POST request. The app must save the secret and use it when encrypting JWT tokens that are generated for Tunnistamo.

```json
{
    "id": "e631942a-79cc-415f-af25-37e0a7c62112",
    "user": "2cbbac99-ce5f-411b-b928-1efc4ca4b877",
    "secret_key": {
        "k": "QVCQYbkffUie9-bX457MoMyKD2gpca18czbT51_V5cI",
        "use": "enc",
        "kty": "oct",
        "alg": "HS256"
    },
    "...": "..."
}
```

### Create a new identity

```
POST <prefix>/v1/user_identity/

Authentication: Bearer <JWT access token>
```

```json
{
    "service": "helmet",
    "identifier": "384729817232",
    "secret": "1234"
}
```

When processing the POST request, Tunnistamo will validate the identifier through a 3rd party. Secrets will only be used in validating the identifier, and they will not be saved to database.

#### Errors

- Credential validation failed

HTTP 401

```json
{
    "code": "invalid_credentials",
    "detail": "Invalid user credentials [or something more specific]"
}
```

- 3rd party authentication service failure

HTTP 401

```json
{
    "code": "authentication_service_unavailable",
    "detail": "Connection to authentication service timed out [or smth else]"
}
```

## NFC

The user may be identified using an NFC-capable application (such as the Open City App).

The user must first log in to Tunnistamo using the application. The application will then register the user's device. To do that, first the application must generate an EC key pair. The public key will be sent to Tunnistamo when registering the new user device. If registration completes successfully, Tunnistamo will generate a shared AES secret key that will be returned to the application.

At authentication time, the user will first present her phone to an NFC reader ("interface device"). The interface device will send a message (an "APDU") selecting the right application using the custom application ID (AID) `f0 74 75 6e 6e 69 73 74 61 6d 6f`.

The interface device will provide its allocated client ID through an EXTERNAL AUTHENTICATE command. For now, the device will not verify it in any way. It will be included in the generated JWT token for access control purposes.

The reader will ask the application to generate a token using the INTERNAL AUTHENTICATE command. The device will respond with an encrypted and signed JWT token which will be passed to Tunnistamo as-is. The JWT token contains:

| field   | description |
| ---     | ---         |
| `iss`   | unique device or app ID |
| `sub`   | user UUID   |
| `iat`   | issued at timestamp |
| `cnt`   | incrementing counter |
| `nonce` | randomly generated integer |
| `azp`   | client ID of the interface device (NFC reader) |

`cnt` and `iat` are used to prevent token re-use attacks, and `nonce` is used to authenticate the NFC reader if needed.

### NFC communication

SELECT AID:
`00 a4 04 00 0b f0 74 75 6e 6e 69 73 74 61 6d 6f 00`

response:
`90 00`

EXTERNAL AUTHENTICATE:
`00 b2 01 01 30 xx xx xx [...]`

response:
`90 00`

INTERNAL AUTHENTICATE:
`00 88 01 01 00 00`

response:
`yy yy yy [...] 90 00`

The bytes marked with `xx` contain the client ID given to the interface device (NFC reader) and the `yy` bytes contain the JWT token in ASCII.

### Exchanging the JWT token for user identity

The token can be used to get user identity information. The interface device must send its client secret in a HTTP header. Optionally, a proprietary interface device ID can also be passed for audit logging purposes.

```
GET /v1/user_identity/

Authorization: Bearer eyJhbGciOiJBMjU2S1ciLCJ[...]
X-Interface-Device-Secret: <interface device client secret>
X-Interface-Device-ID: <proprietary interface device ID>
```

response:

```json
[
    {
        "service": "helmet",
        "identifier": "384729817232",
    }
]
```

The response contains a random nonce generated by the mobile device. It is returned in the HTTP header X-Nonce. A correct nonce is required when retrieving the user's PIN from the mobile device.

### Retrieving the user's PIN

EXTERNAL AUTHENTICATE:
`00 b2 01 02 xx yy yy yy [...]`

In the EXTERNAL AUTHENTICATE command, yy stands for the nonce retrieved in the previous step, as an ASCII-encoded string. xx stands for the length of the ASCII-encoded nonce.
If the nonce is correct, the user's PIN is returned in the response payload, also as an ASCII-encoded string.


#### Errors

- Invalid JWT token

HTTP 401

```json
{
    "detail": "Token has expired. [or smth else]"
}
```

- Invalid interface device credentials

HTTP 401

```json
{
    "detail": "Invalid interface device credentials."
}
```
