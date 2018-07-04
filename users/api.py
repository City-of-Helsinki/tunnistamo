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
