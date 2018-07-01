from rest_framework import mixins, permissions, serializers, viewsets

from tunnistamo.pagination import DefaultPagination
from users.models import UserLoginEntry


class UserLoginEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLoginEntry
        fields = ('service', 'timestamp', 'ip_address', 'geo_location')


class UserLoginEntryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserLoginEntrySerializer
    queryset = UserLoginEntry.objects.all()
    pagination_class = DefaultPagination

    def get_queryset(self):
        return self.queryset.filter(user_id=self.request.user.id)
