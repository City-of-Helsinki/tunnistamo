import pytest


@pytest.mark.django_db
@pytest.mark.parametrize('lang', [None, 'fi', 'sv', 'en'])
def test_language_is_determined_by_django_locale_middleware(lang, client, settings, use_translations):
    headers = {'HTTP_ACCEPT_LANGUAGE': lang} if lang else {}
    response = client.get('/login/', **headers)

    expected_language = lang if lang else settings.LANGUAGE_CODE

    assert f'<html lang="{expected_language}">' in response.rendered_content
