from social_core.backends.azuread_tenant import AzureADV2TenantOAuth2


class VantaaAzureADV2TenantOAuth2(AzureADV2TenantOAuth2):
    name = 'vantaaazuread'

    def get_user_details(self, response):
        details = super().get_user_details(response)
        details['ad_groups'] = response.get('groups')

        return details
