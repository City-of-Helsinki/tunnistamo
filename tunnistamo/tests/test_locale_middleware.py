import pytest
from django.conf import settings


@pytest.mark.django_db
@pytest.mark.parametrize('lang', [None, 'fi', 'sv', 'en'])
@pytest.mark.parametrize('ui_locales', [None, '', 'de'])
def test_language_is_determined_by_django_locale_middleware_if_ui_locales_provides_no_preference(
    lang, ui_locales, client, settings, use_translations
):
    headers = {'HTTP_ACCEPT_LANGUAGE': lang} if lang else {}
    data = {'ui_locales': ui_locales} if ui_locales is not None else {}
    response = client.get('/login/', data, **headers)

    expected_language = lang if lang else settings.LANGUAGE_CODE

    assert f'<html lang="{expected_language}">' in response.rendered_content


NON_DEFAULT_LANGUAGE_CODE = list(filter(lambda lang: lang[0] != settings.LANGUAGE_CODE, settings.LANGUAGES))[0][0]


@pytest.mark.django_db
@pytest.mark.parametrize('ui_locales,expected_lang', [
    (f'{settings.LANGUAGE_CODE}', settings.LANGUAGE_CODE),
    (f'{NON_DEFAULT_LANGUAGE_CODE}', NON_DEFAULT_LANGUAGE_CODE),
    (f'{NON_DEFAULT_LANGUAGE_CODE}-SPECIFIER', NON_DEFAULT_LANGUAGE_CODE),
])
def test_language_is_determined_from_ui_locales_query_parameter(ui_locales, expected_lang, client, use_translations):
    data = {'ui_locales': ui_locales}
    response = client.get('/login/', data)

    assert f'<html lang="{expected_lang}">' in response.rendered_content
