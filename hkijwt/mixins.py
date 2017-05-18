from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _


class AutoFilledIdentifier(object):
    """
    Mixin for auto-filling identifier.
    """
    def clean_fields(self, exclude=None):
        if not self.identifier:
            self.identifier = self._generate_identifier()
        super(AutoFilledIdentifier, self).clean_fields(exclude)

    def __str__(self):
        return self.identifier


class ImmutableFields(object):
    """
    Mixin for checking immutable fields.

    Values of immutable fields should not be changed once saved.
    """
    immutable_fields = []

    def clean_fields(self, exclude=None):
        errors = {}
        try:
            super(ImmutableFields, self).clean_fields(exclude)
        except ValidationError as error:
            error.update_error_dict(errors)

        if self.pk:
            saved = type(self)._default_manager.filter(pk=self.pk).first()
            if saved:
                more_errors = self._check_immutable_fields(saved)
                if more_errors:
                    ValidationError(more_errors).update_error_dict(errors)

        if errors:
            raise ValidationError(errors)

    def _check_immutable_fields(self, saved):
        return {
            field: ValidationError(
                _("Value of field \"{}\" cannot be changed").format(
                    self._meta.get_field(field).verbose_name),
                code='immutable-field')
            for field in self.immutable_fields
            if getattr(self, field) != getattr(saved, field)
        }
