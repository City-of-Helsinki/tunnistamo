from collections import OrderedDict

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError


# copy-pasted from https://github.com/City-of-Helsinki/kerrokantasi/blob/2c26bf3ee9ac4fdc88aefabd7d0c4e73f4d3707d/democracy/views/utils.py#L257  # noqa
class TranslatableSerializer(serializers.Serializer):
    """
    A serializer for translated fields.
    translated_fields must be declared in the Meta class.
    By default, translation languages obtained from settings, but can be overriden
    by defining translation_lang in the Meta class.
    """

    def __init__(self, *args, **kwargs):
        self.Meta.translated_fields = [
            field for field in self.Meta.model._parler_meta._fields_to_model if field in self.Meta.fields
        ]
        non_translated_fields = [field for field in self.Meta.fields if field not in self.Meta.translated_fields]
        self.Meta.fields = non_translated_fields
        super(TranslatableSerializer, self).__init__(*args, **kwargs)
        self.Meta.fields = non_translated_fields + self.Meta.translated_fields
        if not hasattr(self.Meta, 'translation_lang'):
            self.Meta.translation_lang = [lang['code'] for lang in settings.PARLER_LANGUAGES[settings.SITE_ID]]

    def _update_lang(self, ret, field, value, lang_code):
        if not ret.get(field) or isinstance(ret[field], str):
            ret[field] = {}
        if value:
            ret[field][lang_code] = value
        return ret

    def to_representation(self, instance):
        ret = super(TranslatableSerializer, self).to_representation(instance)
        translations = instance.translations.filter(language_code__in=self.Meta.translation_lang)

        for translation in translations:
            for field in self.Meta.translated_fields:
                self._update_lang(ret, field, getattr(translation, field), translation.language_code)
        return ret

    def _validate_translated_field(self, field, data):
        assert field in self.Meta.translated_fields, '%s is not a translated field' % field
        if data is None:
            return
        if not isinstance(data, dict):
            raise ValidationError(_('Not a valid translation format. Expecting {"lang_code": %(data)s}' %
                                    {'data': data}))
        for lang in data:
            if lang not in self.Meta.translation_lang:
                raise ValidationError(_('%(lang)s is not a supported languages (%(allowed)s)' % {
                    'lang': lang,
                    'allowed': self.Meta.translation_lang,
                }))

    def validate(self, data):
        """
        Add a custom validation for translated fields.
        """
        validated_data = super().validate(data)
        errors = OrderedDict()
        for field in self.Meta.translated_fields:
            try:
                self._validate_translated_field(field, data.get(field, None))
            except ValidationError as e:
                errors[field] = e.detail

        if errors:
            raise ValidationError(errors)

        return validated_data

    def to_internal_value(self, value):
        ret = super(TranslatableSerializer, self).to_internal_value(value)
        for field in self.Meta.translated_fields:
            v = value.get(field)
            if v:
                ret[field] = v
        return ret

    def save(self, **kwargs):
        """
        Extract the translations and save them after main object save.
        """
        translated_data = self._pop_translated_data()
        if not self.instance:
            # forces the translation to be created, since the object cannot be saved without
            self.validated_data[self.Meta.translated_fields[0]] = ''
        instance = super(TranslatableSerializer, self).save(**kwargs)
        self.save_translations(instance, translated_data)
        instance.save()
        return instance

    def _pop_translated_data(self):
        """
        Separate data of translated fields from other data.
        """
        translated_data = {}
        for meta in self.Meta.translated_fields:
            translations = self.validated_data.pop(meta, {})
            if translations:
                translated_data[meta] = translations
        return translated_data

    def save_translations(self, instance, translated_data):
        """
        Save translation data into translation objects.
        """
        for field in self.Meta.translated_fields:
            translations = {}
            if not self.partial:
                translations = {lang_code: '' for lang_code in self.Meta.translation_lang}
            translations.update(translated_data.get(field, {}))

            for lang_code, value in translations.items():
                translation = instance._get_translated_model(lang_code, auto_create=True)
                setattr(translation, field, value)
        instance.save_translations()


def assert_objects_in_response(response, objects):
    assert {r['id'] for r in response.data['results']} == {o.id for o in objects}
