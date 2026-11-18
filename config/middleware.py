from django.conf import settings
from django.middleware.locale import LocaleMiddleware
from django.utils import translation

class LanguagePreferenceMiddleware(LocaleMiddleware):
    """Use Spanish until the visitor explicitly chooses another language."""

    def process_request(self, request):
        language = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        if language not in dict(settings.LANGUAGES):
            language = settings.LANGUAGE_CODE
        translation.activate(language)
        request.LANGUAGE_CODE = language
