from django.core.management.base import BaseCommand, CommandError
from oidc_provider.models import Client

from oidc_apis.models import ApiScope


class Command(BaseCommand):
    help = "Add New Client OpenID Connect API Scope"

    def add_arguments(self, parser):
        parser.add_argument(
            "-c", "--client_id", type=str, help="Client ID", required=True
        )
        parser.add_argument(
            "-asi",
            "--api_scope_identifier",
            type=str,
            help="API Scope Identifier",
            required=True,
        )

    def handle(self, *args, **kwargs):
        apiScope = ApiScope.objects.filter(
            identifier=kwargs["api_scope_identifier"]
        ).first()
        if not apiScope:
            raise CommandError(
                'No API Scope with identifier "%s" found'
                % kwargs["api_scope_identifier"]
            )

        client = Client.objects.filter(client_id=kwargs["client_id"]).first()

        if not client:
            raise CommandError(
                'No Client with identifier "%s" found' % kwargs["client_id"]
            )

        apiScope.allowed_apps.add(client)
