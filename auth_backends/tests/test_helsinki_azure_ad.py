import json

from auth_backends.tests.azure_ad_base import AzureADV2TenantOAuth2Test, _generate_access_token_body


class TestSocialAuthOidFromSubClaim(AzureADV2TenantOAuth2Test):
    backend_path = 'auth_backends.helsinki_azure_ad.HelsinkiAzureADTenantOAuth2'
    access_token_body = _generate_access_token_body()

    def test_login(self):
        user = self.do_login()

        self.assertEqual(
            user.social_auth.first().uid,
            'v-T_abcdefgABCDEFGabcdefgABCDEFGabcdefgABCD'
        )


class TestNoErrorWhenADGroupsNotInTokenOrGraph(AzureADV2TenantOAuth2Test):
    backend_path = 'auth_backends.helsinki_azure_ad.HelsinkiAzureADTenantOAuth2'
    access_token_body = _generate_access_token_body(extra_payload={
        'groups': None,
    })

    def setup_graph_response(self, **kwargs):
        super().setup_graph_response(status=400)

    def test_login(self):
        user = self.do_login()

        self.assertEqual(user.ad_groups.count(), 0)


class TestADGroupsFromGraphResponse(AzureADV2TenantOAuth2Test):
    backend_path = 'auth_backends.helsinki_azure_ad.HelsinkiAzureADTenantOAuth2'
    access_token_body = _generate_access_token_body(extra_payload={
        '_claim_names': {
            'groups': 'src1'
        },
        '_claim_sources': {
            'src1': {
                'endpoint': (
                    'https://graph.windows.net/00000000-0000-0000-0000-000000000000'
                    '/users/00000000-0000-0000-0000-000000000000/getMemberObjects'
                )
            }
        },
    })

    def setup_graph_response(self, **kwargs):
        body = json.dumps({
            '@odata.context': 'https://graph.microsoft.com/beta/$metadata#directoryObjects',
            'value': [
                {
                    '@odata.type': '#microsoft.graph.group',
                    'id': '00000000-0000-4000-a0000000000000000',
                    'displayName': 'first_group',
                    'securityEnabled': True,
                },
                {
                    '@odata.type': '#microsoft.graph.group',
                    'id': '00000000-0000-4000-a0000000000000001',
                    'displayName': 'Second group',
                    'securityEnabled': True,
                },
                {
                    '@odata.type': '#microsoft.graph.group',
                    'id': '00000000-0000-4000-a0000000000000002',
                    'displayName': 'Third Group',
                    'securityEnabled': False,
                },
            ],
        })

        super().setup_graph_response(body=body)

    def test_login(self):
        user = self.do_login()

        self.assertCountEqual(
            ['first_group', 'second group'],
            user.ad_groups.values_list('name', flat=True)
        )


class TestADGroupsFromToken(AzureADV2TenantOAuth2Test):
    backend_path = 'auth_backends.helsinki_azure_ad.HelsinkiAzureADTenantOAuth2'
    access_token_body = _generate_access_token_body(extra_payload={
        'groups': [
            'In-claim group 1',
            'In-claim group 2',
        ],
    })

    def setup_graph_response(self, **kwargs):
        super().setup_graph_response(status=400)

    def test_login(self):
        user = self.do_login()

        self.assertCountEqual(
            ['in-claim group 1', 'in-claim group 2'],
            user.ad_groups.values_list('name', flat=True)
        )


class TestADGroupsFromGraphResponseWhenAlsoTokenHasGroups(AzureADV2TenantOAuth2Test):
    backend_path = 'auth_backends.helsinki_azure_ad.HelsinkiAzureADTenantOAuth2'
    access_token_body = _generate_access_token_body(extra_payload={
        'groups': [
            'In-claim group 1',
            'In-claim group 2',
        ],
    })

    def setup_graph_response(self, **kwargs):
        body = json.dumps({
            '@odata.context': 'https://graph.microsoft.com/beta/$metadata#directoryObjects',
            'value': [
                {
                    '@odata.type': '#microsoft.graph.group',
                    'id': '00000000-0000-4000-a0000000000000000',
                    'displayName': 'first_group',
                    'securityEnabled': True,
                },
                {
                    '@odata.type': '#microsoft.graph.group',
                    'id': '00000000-0000-4000-a0000000000000001',
                    'displayName': 'Second group',
                    'securityEnabled': True,
                }
            ],
        })

        super().setup_graph_response(body=body)

    def test_login(self):
        user = self.do_login()

        self.assertCountEqual(
            ['first_group', 'second group'],
            user.ad_groups.values_list('name', flat=True)
        )
