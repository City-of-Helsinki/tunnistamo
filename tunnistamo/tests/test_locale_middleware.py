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
UI_LOCALES_TEST_VALUES = [
    (f'{settings.LANGUAGE_CODE} {NON_DEFAULT_LANGUAGE_CODE}', settings.LANGUAGE_CODE),
    (f'{NON_DEFAULT_LANGUAGE_CODE} {settings.LANGUAGE_CODE}', NON_DEFAULT_LANGUAGE_CODE),
    (f'{NON_DEFAULT_LANGUAGE_CODE}-SPECIFIER {settings.LANGUAGE_CODE}', NON_DEFAULT_LANGUAGE_CODE),
    (f'de unknown  {NON_DEFAULT_LANGUAGE_CODE}  ', NON_DEFAULT_LANGUAGE_CODE),
]


@pytest.mark.django_db
@pytest.mark.parametrize('ui_locales,expected_lang', UI_LOCALES_TEST_VALUES)
def test_language_is_determined_from_ui_locales_query_parameter(ui_locales, expected_lang, client, use_translations):
    data = {'ui_locales': ui_locales}
    response = client.get('/login/', data)

    assert f'<html lang="{expected_lang}">' in response.rendered_content


@pytest.mark.django_db
@pytest.mark.parametrize('ui_locales,expected_lang', UI_LOCALES_TEST_VALUES)
def test_ui_locales_is_remembered_and_used_during_a_session(ui_locales, expected_lang, client, use_translations):
    # Stores the ui_locales into the session
    data = {'ui_locales': ui_locales}
    client.get('/login/', data)

    # Uses the ui_locales from the session
    response = client.get('/login/')

    assert f'<html lang="{expected_lang}">' in response.rendered_content
