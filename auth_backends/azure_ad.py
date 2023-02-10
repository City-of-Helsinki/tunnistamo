from social_core.backends.azuread_tenant import AzureADV2TenantOAuth2


class AzureADV2TenantOAuth2WithADGroups(AzureADV2TenantOAuth2):
    def get_user_details(self, response):
        details = super().get_user_details(response)
        details['ad_groups'] = response.get('groups')

        return details
