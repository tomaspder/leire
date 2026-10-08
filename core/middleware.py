from django.utils.cache import add_never_cache_headers


class PrivateResponseMiddleware:
    """Evita indexación y que proxies o navegadores guarden páginas con datos."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["X-Robots-Tag"] = "noindex, nofollow"
        if not request.path.startswith("/static/"):
            add_never_cache_headers(response)
            response["Cache-Control"] += ", private"
        return response
