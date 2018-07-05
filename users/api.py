from oidc_provider.models import UserConsent
from rest_framework import mixins, serializers, viewsets
from rest_framework.permissions import IsAuthenticated

from tunnistamo.api_common import OidcTokenAuthentication, ScopePermission
from tunnistamo.pagination import DefaultPagination
from users.models import UserLoginEntry


class UserLoginEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLoginEntry
        fields = ('service', 'timestamp', 'ip_address', 'geo_location')


class UserLoginEntryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = UserLoginEntrySerializer
    queryset = UserLoginEntry.objects.all()
    pagination_class = DefaultPagination
    authentication_classes = (OidcTokenAuthentication,)
    permission_classes = (IsAuthenticated, ScopePermission)
    required_scopes = ('login_entries',)

    def get_queryset(self):
        return self.queryset.filter(user_id=self.request.user.id)


class UserConsentSerializer(serializers.ModelSerializer):
    service = serializers.SerializerMethodField()
    scopes = serializers.SerializerMethodField()

    class Meta:
        model = UserConsent
        fields = ('id', 'date_given', 'expires_at', 'service', 'scopes')

    def get_service(self, obj):
        return obj.client.service.id

    def get_scopes(self, obj):
        return [s for s in obj.scope if s != 'openid']


class UserConsentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin,
                         viewsets.GenericViewSet):
    serializer_class = UserConsentSerializer
    queryset = UserConsent.objects.select_related('client__service')
    pagination_class = DefaultPagination
    authentication_classes = (OidcTokenAuthentication,)
    permission_classes = (IsAuthenticated, ScopePermission)
    required_scopes = ('consents',)

    def get_queryset(self):
        return self.queryset.filter(user_id=self.request.user.id).exclude(client__service=None)
