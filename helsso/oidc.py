from django.utils.translation import ugettext_lazy as _
from oidc_provider.lib.claims import ScopeClaims


def sub_generator(user):
    return str(user.uuid)


class GithubScopeClaims(ScopeClaims):
    info_github = (_("GitHub"), _("GitHub username"))

    def scope_github(self):
        social_accounts = self.user.socialaccount_set
        github_account = social_accounts.filter(provider='github').first()
        if not github_account:
            return {}
        github_data = github_account.extra_data
        return {
            'github': {
                'login': github_data.get('login'),
            },
        }
