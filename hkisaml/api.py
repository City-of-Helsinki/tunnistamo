import jwt

from django.contrib.auth import get_user_model
from rest_framework import permissions, serializers, generics, mixins, views
from rest_framework.response import Response
from oauth2_provider.ext.rest_framework import TokenHasReadWriteScope


class UserSerializer(serializers.ModelSerializer):
    def to_representation(self, obj):
        ret = super(UserSerializer, self).to_representation(obj)
        if obj.first_name and obj.last_name:
            ret['display_name'] = '%s %s' % (obj.first_name, obj.last_name)
        return ret

    class Meta:
        fields = [
            'last_login', 'username', 'email', 'date_joined',
            'first_name', 'last_name', 'uuid', 'department_name'
        ]
        model = get_user_model()


# ViewSets define the view behavior.
class UserView(generics.RetrieveAPIView,
               mixins.RetrieveModelMixin):
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        else:
            return self.queryset.filter(pk=user.pk)

    def get_object(self):
        username = self.kwargs.get('username', None)
        if username:
            qs = self.get_queryset()
            obj = generics.get_object_or_404(qs, username=username)
        else:
            obj = self.request.user
        return obj

    permission_classes = [permissions.IsAuthenticated, TokenHasReadWriteScope]
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer


class GetJWTView(views.APIView):
    # permission_classes = [permissions.IsAuthenticated, TokenHasReadWriteScope]
    def get(self, request, format=None):
        secret = '12345'
        user = get_user_model().objects.first()
        payload = UserSerializer(user).data
        encoded = jwt.encode(payload, secret, algorithm='HS256')
        return Response({'token': encoded})


#router = routers.DefaultRouter()
#router.register(r'users', UserViewSet)
