from django.contrib.auth.models import User
from rest_framework import permissions, routers, serializers, generics, mixins
from oauth2_provider.ext.rest_framework import TokenHasReadWriteScope


class UserSerializer(serializers.ModelSerializer):
    def to_representation(self, obj):
        ret = super(UserSerializer, self).to_representation(obj)
        if hasattr(obj, 'profile'):
            ret['department_name'] = obj.profile.department_name
        return ret

    class Meta:
        fields = [
            'last_login', 'username', 'email', 'date_joined',
            'first_name', 'last_name'
        ]
        model = User


# ViewSets define the view behavior.
class UserView(generics.RetrieveAPIView,
               mixins.RetrieveModelMixin):
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        else:
            return self.queryset.filter(id=user.id)

    def get_object(self):
        username = self.kwargs.get('username', None)
        if username:
            qs = self.get_queryset()
            obj = generics.get_object_or_404(qs, username=username)
        else:
            obj = self.request.user
        return obj

    permission_classes = [permissions.IsAuthenticated, TokenHasReadWriteScope]
    queryset = User.objects.all()
    serializer_class = UserSerializer


#router = routers.DefaultRouter()
#router.register(r'users', UserViewSet)
