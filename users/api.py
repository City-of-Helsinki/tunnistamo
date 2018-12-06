import coreapi
import coreschema
from oidc_provider.models import UserConsent
from rest_framework import filters, mixins, serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.schemas import AutoSchema

from scopes.api import ScopeDataBuilder
from tunnistamo.api_common import OidcTokenAuthentication, ScopePermission
from tunnistamo.pagination import DefaultPagination
from users.models import UserLoginEntry


class UserLoginEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLoginEntry
        fields = ('service', 'timestamp', 'ip_address', 'geo_location')


class UserLoginEntryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    List service login entries.

    list:
    Return all login entries of the current user.
    """
    serializer_class = UserLoginEntrySerializer
    queryset = UserLoginEntry.objects.all()
    pagination_class = DefaultPagination
    authentication_classes = (OidcTokenAuthentication,)
    permission_classes = (IsAuthenticated, ScopePermission)
    required_scopes = ('login_entries',)
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ('timestamp',)

    def get_queryset(self):
        return self.queryset.filter(user_id=self.request.user.id)


class UserConsentSerializer(serializers.ModelSerializer):
    service = serializers.SerializerMethodField()
    scopes = serializers.SerializerMethodField()

    class Meta:
        model = UserConsent
        fields = ('id', 'date_given', 'expires_at', 'service', 'scopes')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._scope_data_builder = ScopeDataBuilder()

    def get_service(self, obj):
        return obj.client.service.id

    def get_scopes(self, obj):
        scopes = [s for s in obj.scope if s != 'openid']

        if 'scope' in self.context.get('expanded_fields', ()):
            return self._scope_data_builder.get_scopes_data(scopes)
        else:
            return scopes


class UserConsentViewSchema(AutoSchema):
    def get_filter_fields(self, path, method):
        fields = super().get_filter_fields(path, method)

        if self.view.action in ('list', 'retrieve'):
            schema = coreschema.String(
                title='Include',
                description='A comma-separated list of fields for which the full data of the related resource(s) should'
                            ' be included nested in the response. Currently supports only "scope".'
            )
            fields.append(coreapi.Field(name='include', required=False, location='query', schema=schema))

        return fields


class UserConsentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin,
                         viewsets.GenericViewSet):
    """
    List consents given to services.

    retrieve:
    Return a consent instance.

    list:
    Return all consents given by the current user.

    delete:
    Delete a consent instance.
    """
    serializer_class = UserConsentSerializer
    queryset = UserConsent.objects.select_related('client__service')
    pagination_class = DefaultPagination
    authentication_classes = (OidcTokenAuthentication,)
    permission_classes = (IsAuthenticated, ScopePermission)
    required_scopes = ('consents',)
    schema = UserConsentViewSchema()

    def get_queryset(self):
        if not self.request:
            return self.queryset.none()

        return self.queryset.filter(user_id=self.request.user.id).exclude(client__service=None)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['expanded_fields'] = [s.strip() for s in self.request.GET.get('include', '').split(',')]
        return context
