import datetime
from collections.abc import Iterable
from urllib.parse import urlparse

from django.db.models import Max
from django.urls import reverse
from django.views.generic.base import TemplateView
from oauth2_provider.models import AccessToken
from oidc_provider.models import Client, Token

from hkijwt.models import AppToAppPermission
from oidc_apis.models import Api, ApiScope
from users.models import Application, OidcClientOptions


def configured_domains(app):
    hosts = set()
    for field in ['redirect_uris', 'post_logout_redirect_uris', '_post_logout_redirect_uris', '_redirect_uris']:
        urls = getattr(app, field, None)
        if urls is None:
            continue
        if isinstance(urls, str):
            urls = urls.splitlines()
        for url in urls:
            netloc = urlparse(url.strip()).netloc
            if len(netloc.strip()) > 0:
                hosts.add(netloc)
    return hosts


def report_oidc_clients():
    queryset = Token.objects.values('client_id').annotate(latest=Max('expires_at')).order_by('-latest')
    timestamps_by_client = dict((t['client_id'], t['latest']) for t in queryset)

    uis = set(ApiScope.objects.values_list('allowed_apps__id', flat=True).distinct())
    apis = set(Api.objects.values_list('oidc_client_id', flat=True).distinct())

    def ui_or_api(client):
        if client.id in apis:
            return 'api'
        if client.id in uis:
            return 'ui'
        return 'unknown'

    for client in Client.objects.select_related('options').all():

        try:
            options = client.options
            status = options.site_type
            AD_enabled = options.include_ad_groups
            login_methods = [l.provider_id for l in options.login_methods.all()]
        except OidcClientOptions.DoesNotExist:
            status = None
            AD_enabled = None
            login_methods = None

        cdata = dict(
            authentication_protocol='OpenID Connect',
            client_id=client.client_id,
            name=client.name,
            owner=client.owner,
            client_type=client.client_type,
            response_types=[str(rtype) for rtype in client.response_types.all()],
            date_created=client.date_created,
            last_token=timestamps_by_client.get(client.id),
            website_url=client.website_url,
            contact_email=client.contact_email,
            hosts=configured_domains(client),
            status=status,
            ui_or_api=ui_or_api(client),
            AD_enabled=AD_enabled,
            login_methods=login_methods,
            modify='<a href="{}">edit</a>'.format(reverse(
                'admin:oidc_provider_client_change', args=[client.id]))
        )
        yield cdata


def report_oauth_clients():
    queryset = AccessToken.objects.values('application_id').annotate(latest=Max('updated')).order_by('-latest')
    timestamps_by_client = dict((t['application_id'], t['latest']) for t in queryset)

    uis = set(AppToAppPermission.objects.values_list('requester__id', flat=True).distinct())
    apis = set(AppToAppPermission.objects.values_list('target__id', flat=True).distinct())

    def ui_or_api(client):
        if client.id in apis:
            return 'api'
        if client.id in uis:
            return 'ui'
        return 'unknown'

    for client in Application.objects.all():
        login_methods = [l.provider_id for l in client.login_methods.all()]
        cdata = dict(
            authentication_protocol='OAuth2',
            client_id=client.client_id,
            name=client.name,
            owner=client.user,
            client_type=client.client_type,
            response_types=[client.authorization_grant_type],
            last_token=timestamps_by_client.get(client.id),
            date_created=client.created,
            website_url='',
            contact_email='',
            hosts=configured_domains(client),
            status=client.site_type,
            ui_or_api=ui_or_api(client),
            AD_enabled=client.include_ad_groups,
            login_methods=login_methods,
            modify='<a href="{}">edit</a>'.format(reverse(
                'admin:users_application_change', args=[client.id]))
        )
        yield cdata


def compare(x):
    value = x['last_token']
    if value is None:
        value = datetime.datetime(year=1970, month=1, day=1, tzinfo=datetime.timezone.utc)
    return value


def report():
    clients = [client for client in list(report_oidc_clients()) + list(report_oauth_clients())]
    return sorted(clients, key=compare)


class ReportView(TemplateView):
    template_name = "report.html"

    def get_context_data(self, **kwargs):
        context = super(ReportView, self).get_context_data(**kwargs)
        clients = report()
        headers = clients[0].keys()
        context['headers'] = [k.replace('_', ' ') for k in headers]

        def format_value(value):
            if isinstance(value, Iterable) and not isinstance(value, str):
                return ",\n".join(value)
            return value

        context['clients'] = [
            [format_value(client.get(key)) for key in headers] for client in clients
        ]
        return context
