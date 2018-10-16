from django.db.models import Exists, OuterRef
from django.db.models.functions import Greatest
from django.utils.translation import ugettext_lazy as _
from django_filters import rest_framework as filters
from django_filters.widgets import BooleanWidget
from oauth2_provider.models import AccessToken
from oidc_provider.models import UserConsent
from rest_framework import serializers, viewsets

from services.models import Service
from tunnistamo.api_common import OidcTokenAuthentication, TokenAuth
from tunnistamo.pagination import DefaultPagination
from tunnistamo.utils import TranslatableSerializer


class ServiceSerializer(TranslatableSerializer):
    # these are required because of TranslatableSerializer
    id = serializers.IntegerField(label='ID', read_only=True)
    image = serializers.ImageField(allow_null=True, max_length=100, required=False)

    class Meta:
        model = Service
        fields = ('id', 'name', 'url', 'description', 'image')

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if hasattr(instance, 'consent_given'):
            data['consent_given'] = instance.consent_given

        return data


class ServiceFilter(filters.FilterSet):
    consent_given = filters.Filter(
        method='filter_consent_given', widget=BooleanWidget(),
        help_text=_('Include only services that have or don\'t have a consent given by the current user. '
                    'Accepts boolean values "true" and "false".'))

    class Meta:
        model = Service
        fields = ('consent_given',)

    def filter_consent_given(self, queryset, name, value):
        if 'consent_given' in queryset.query.annotations.keys():
            queryset = queryset.filter(consent_given=value)

        return queryset


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List services.

    retrieve:
    Return a service instance.

    list:
    Return all services.
    """
    serializer_class = ServiceSerializer
    queryset = Service.objects.all()
    pagination_class = DefaultPagination
    filterset_class = ServiceFilter
    authentication_classes = (OidcTokenAuthentication,)

    def get_queryset(self):
        queryset = super().get_queryset()

        if not self.request:
            return queryset

        user = self.request.user

        if user.is_authenticated and isinstance(self.request.auth, TokenAuth):
            token_domains = self.request.auth.scope_domains
            consent_perms = token_domains.get('consents', set())
            consent_read_perm_included = any('read' in perm[0] and perm[1] is None for perm in consent_perms)

            if consent_read_perm_included:
                user_consents = UserConsent.objects.filter(client__service=OuterRef('pk'), user=user)
                user_access_tokens = AccessToken.objects.filter(application__service=OuterRef('pk'), user=user)
                queryset = queryset.annotate(
                    consent_given=Greatest(Exists(user_consents), Exists(user_access_tokens))
                )

        return queryset
