# Authenticating using user-controlled devices

Tunnistamo supports authenticating users through user-controlled devices. The only device we currently support is a mobile phone that has the [Open City App](https://github.com/City-of-Helsinki/open-city-app) installed.

## Login and registration

### Login

The user must be authenticated to Tunnistamo first. We support only browser-based login, so for native applications some kind of integrated browser (such as WebView) must be used.

After the user completes the login flow, an access token is provided to the application. The app must then generate an Elliptic Curve (EC) key pair on the NIST P-256 curve. The new device is then registered with a `POST` request to the `/v1/user_device/` endpoint.

```
POST <prefix>/v1/user_device/

Authentication: Bearer <JWT access token>
```

```json
{
    "identifier": "e631942a-79cc-415f-af25-37e0a7c62112",
    "public_key": {
        "kty": "EC",
        "use": "sig",
        "crv": "P-256",
        "x": "UdTokfffnUeczbK2-7QuBq_YaDgXek6IreqhGZ1cR4s",
        "y": "NBJKDLcZejGp1msCzHRNopykrEbktsqWsk4hGdr6gPk",
        "alg": "ES256"
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
    "id": 3821,
    "user": "2cbbac99-ce5f-411b-b928-1efc4ca4b877",
    "identifier": "e631942a-79cc-415f-af25-37e0a7c62112",
    "shared_key": {
        "k": "QVCQYbkffUie9-bX457MoMyKD2gpca18czbT51_V5cI",
        "use": "enc",
        "kty": "oct",
        "alg": "HS256"
    }
    ...
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

The user may be identified using an NFC-capable application.

The user must first log in to Tunnistamo using the application. The application will then generate an EC key pair and send the public key to Tunnistamo by registering the user's device. If registration completes successfully, Tunnistamo will generate a shared secret key that will be returned to the application.

At authentication time, the user will first present her phone to an NFC reader. The NFC reader will send a message (an "APDU") selecting the right application using the custom application ID (AID) `f0 74 75 6e 6e 69 73 74 61 6d 6f`. Then the reader will ask the application to generate a token using the INTERNAL AUTHENTICATE command.

The device will respond with an encrypted and signed JWT token which will be passed to Tunnistamo as-is. The JWT token contains:

| field   | description |
| ---     | ---         |
| `iss`   | unique device or app ID |
| `sub`   | user UUID   |
| `iat`   | issued at timestamp |
| `cnt`   | incrementing counter |
| `nonce` | randomly generated integer |

`cnt` and `iat` are used to prevent token re-use attacks, and `nonce` is used to authenticate the NFC reader if needed.

SELECT AID: `00 a4 04 00 0b f0 74 75 6e 6e 69 73 74 61 6d 6f 00` 
response: `90 00`
INTERNAL AUTHENTICATE: `00 88 01 01 00 00`
response: `xx xx xx [...] 90 00`
