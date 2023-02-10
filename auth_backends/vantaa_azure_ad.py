from auth_backends.azure_ad import AzureADV2TenantOAuth2WithADGroups


class VantaaAzureADV2TenantOAuth2(AzureADV2TenantOAuth2WithADGroups):
    name = 'vantaaazuread'
