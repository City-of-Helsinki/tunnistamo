from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext as _
from django.db import transaction
from rest_framework import exceptions


def oidc_to_user_data(payload):
    """
    Map OIDC claims to Django user fields.
    """
    payload = payload.copy()

    field_map = {
        'given_name': 'first_name',
        'family_name': 'last_name',
        'email': 'email',
    }
    ret = {}
    for token_attr, user_attr in field_map.items():
        if token_attr not in payload:
            continue
        ret[user_attr] = payload.pop(token_attr)
    ret.update(payload)

    return ret


def populate_user(user, data):
    exclude_fields = ['is_staff', 'password', 'is_superuser', 'id']
    user_fields = [f.name for f in user._meta.fields
                   if f.name not in exclude_fields]
    changed = False
    for field in user_fields:
        if field in data:
            val = data[field]
            if getattr(user, field) != val:
                setattr(user, field, val)
                changed = True

    return changed


def update_user(user, payload, oidc=False):
    if oidc:
        payload = oidc_to_user_data(payload)

    changed = populate_user(user, payload)
    if changed or not user.pk:
        user.save()

    ad_groups = payload.get('ad_groups', None)
    # Only update AD groups if it's a list of non-empty strings
    if isinstance(ad_groups, list) and (
            all([isinstance(x, str) and x for x in ad_groups])):
        user.update_ad_groups(ad_groups)


def get_or_create_user(payload, oidc=False):
    user_id = payload.get('sub')
    if not user_id:
        msg = _('Invalid payload.')
        raise exceptions.AuthenticationFailed(msg)

    user_model = get_user_model()

    with transaction.atomic():
        try:
            user = user_model.objects.select_for_update().get(uuid=user_id)
        except user_model.DoesNotExist:
            user = user_model(uuid=user_id)
            user.set_unusable_password()
        update_user(user, payload, oidc)

    # If allauth.socialaccount is installed, create the SocialAcount
    # that corresponds to this user. Otherwise logins through
    # allauth will not work for the user later on.
    if 'allauth.socialaccount' in settings.INSTALLED_APPS:
        from allauth.socialaccount.models import SocialAccount, EmailAddress

        if oidc:
            provider_name = 'helsinki_oidc'
        else:
            provider_name = 'helsinki'
        args = {'provider': provider_name, 'uid': user_id}
        try:
            account = SocialAccount.objects.get(**args)
            assert account.user_id == user.id
        except SocialAccount.DoesNotExist:
            account = SocialAccount(**args)
            account.extra_data = payload
            account.user = user
            account.save()

            try:
                email = EmailAddress.objects.get(email__iexact=user.email)
                assert email.user == user
            except EmailAddress.DoesNotExist:
                email = EmailAddress(email=user.email.lower(), primary=True,
                                     user=user, verified=True)
                email.save()

    return user
