import uuid

from auth_backends.adfs.base import BaseADFS


class EspooADFS(BaseADFS):
    """Espoo ADFS authentication backend"""
    name = 'espoo_adfs'
    AUTHORIZATION_URL = 'https://fs.espoo.fi/adfs/oauth2/authorize'
    ACCESS_TOKEN_URL = 'https://fs.espoo.fi/adfs/oauth2/token'

    resource = 'https://varaamo.hel.fi/tuotanto_new'
    domain_uuid = uuid.UUID('5b2401e0-7bbc-485b-8502-18920813a7d0')
    realm = 'espoo'
    cert = (
        'MIIG1zCCBL+gAwIBAgITGgAAfQoAbggMFZQDYAAAAAB9CjANBgkqhkiG9w0BAQsF'
        'ADBaMRQwEgYKCZImiZPyLGQBGRYEY2l0eTESMBAGCgmSJomT8ixkARkWAmFkMRUw'
        'EwYKCZImiZPyLGQBGRYFZXNwb28xFzAVBgNVBAMTDkVzcG9vIEggU3ViIENBMB4X'
        'DTE3MTEyMjEzMDIxMVoXDTIyMTEyMjEzMTIxMVowKDEmMCQGA1UEAxMdQURGUyBT'
        'aWduIC0gZnMuZXNwb28uZmkgU0hBLTIwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAw'
        'ggEKAoIBAQCpNY8Z85B2zlNTJlVRjenLKGNRVOc0+Q/Ll+mA4W0+epMtWl5ljZQU'
        'kWVBOm3vxT2Z5BcEDuv8eygl2R5eqVAExxAfxKbFuC2QrRTvl4frkdi0juVOY/Vs'
        'AZVm6TxMvX4eletZT8iGdb6Al40EriFtdPrTX5NhoTG6YwcQtFa7UHstjsxDktb+'
        'ZXphpPoFB65kSi948ThVPdo6UwIhLKioSw/zVUyfziRstce55CvqKdPbrhXZYRx4'
        'dQY1gKScfbD1XMi+wVMwhp5Abn4D9BNbesMNsZqYHdzyANwMLqszJ6ASRuWoW4xp'
        '/sjs/cs16HDOYyTHy09ppaCUx3wD7tqfAgMBAAGjggLGMIICwjA+BgkrBgEEAYI3'
        'FQcEMTAvBicrBgEEAYI3FQiE3KFUgeH0QIS5mziD5egZh7aYPoEbhtfpHYSAlToC'
        'AWQCAQYwEwYDVR0lBAwwCgYIKwYBBQUHAwEwDgYDVR0PAQH/BAQDAgWgMBsGCSsG'
        'AQQBgjcVCgQOMAwwCgYIKwYBBQUHAwEwHQYDVR0OBBYEFA3f0BbRJG1stycIZ+gZ'
        'djezdJ3mMB8GA1UdIwQYMBaAFKnS5DPbd9hr720Fh3H1s8Djw+GXMIH+BgNVHR8E'
        'gfYwgfMwgfCgge2ggeqGLGh0dHA6Ly9wa2kuZXNwb28uZmkvRXNwb28lMjBIJTIw'
        'U3ViJTIwQ0EuY3JshoG5bGRhcDovLy9DTj1Fc3BvbyUyMEglMjBTdWIlMjBDQSxD'
        'Tj1zLWgtY2EtMDMsQ049Q0RQLENOPVB1YmxpYyUyMEtleSUyMFNlcnZpY2VzLENO'
        'PVNlcnZpY2VzLENOPUNvbmZpZ3VyYXRpb24sREM9YWQsREM9Y2l0eT9jZXJ0aWZp'
        'Y2F0ZVJldm9jYXRpb25MaXN0P2Jhc2U/b2JqZWN0Q2xhc3M9Y1JMRGlzdHJpYnV0'
        'aW9uUG9pbnQwgfwGCCsGAQUFBwEBBIHvMIHsMDgGCCsGAQUFBzAChixodHRwOi8v'
        'cGtpLmVzcG9vLmZpL0VzcG9vJTIwSCUyMFN1YiUyMENBLmNydDCBrwYIKwYBBQUH'
        'MAKGgaJsZGFwOi8vL0NOPUVzcG9vJTIwSCUyMFN1YiUyMENBLENOPUFJQSxDTj1Q'
        'dWJsaWMlMjBLZXklMjBTZXJ2aWNlcyxDTj1TZXJ2aWNlcyxDTj1Db25maWd1cmF0'
        'aW9uLERDPWFkLERDPWNpdHk/Y0FDZXJ0aWZpY2F0ZT9iYXNlP29iamVjdENsYXNz'
        'PWNlcnRpZmljYXRpb25BdXRob3JpdHkwDQYJKoZIhvcNAQELBQADggIBAIGhXVtM'
        'rRq2dNz66P1eO+NzZoV7g5RrN/tcOsBvplj4QjhIeyG9I22eESZNHrege0qZDHng'
        'tkvYaKsIcrU0JAyK+2++D+1mLEVPsr0yo8GRnS3ROGRdm5tH52dt/esaGXmBCPoW'
        'B4c4r8QeDXn7zcVvh0Z0FbIskAVEA9MoWdo7+uTMb/I+K6h97A9ysg9ry2bwAv/B'
        'UletFRVJtMRHqDHd9QeS/G1EmkOP/PstDK5REN9TMo/EUpXYV1mNJF7k0TRtpXu1'
        'pd14EaD2xI993Tf4Vzmeht34RjuKMGS3Rwn6DV4OoTr/49RlO6HARnkLrDz7hAT8'
        '+CVM2iTOuDoswyP6Slbt/vZh9KJB+0g4f/GZCrcsq44DfpxEPAyomIAmSi0TPsjQ'
        'mvQDQQXieY9b6ojxleHMGMD27GpTszXkmtS01Imwy2X7yeZyPEJuPyr0xW2tC6t9'
        'ilyfuetzFr9cNawj2z0JvObVQ8X68Bq0MTBiMdtA/IWgzukGlFhCrLG+KCn/Idqz'
        'dtXrlETkTPhKlm84Pr3MbEueS0MuIwGf6TGUt7arWJe6zDMf1/ZfBQV1kOjFOH6S'
        'DNQhLHEL0mYumZUawi+EaNQOtTE8SN1tbKicI09WR0jdvNs7lvePrB/K1q19hz5m'
        'U+rbNk9+8Jgpzd5ielj37oqQOJazbSxNt+xF'
    )

    def clean_attributes(self, attrs_in):
        attr_map = {
            'primarysid': 'primary_sid',
            'given_name': 'first_name',
            'family_name': 'last_name',
            'email': 'email',
        }
        attrs = {}
        for in_name, out_name in attr_map.items():
            val = attrs_in.get(in_name, None)
            if val is not None:
                if out_name in ('department_name', 'email', 'username'):
                    val = val.lower()
                attrs[out_name] = val
            attrs[out_name] = val
        return attrs
