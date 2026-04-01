from django.http import JsonResponse
from websites.models import Website


class DomainValidationMiddleware:
    """
    Validates API key and domain origin
    ONLY for public chat widget endpoints
    NOT for dashboard/owner endpoints
    """

    # these paths are for widget use only
    WIDGET_PATHS = [
        '/api/chat/widget/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # only validate widget endpoints
        # sessions, detail etc are JWT protected (owner endpoints)
        if any(request.path.startswith(path) for path in self.WIDGET_PATHS):
            api_key = request.headers.get('X-API-Key')
            origin = request.headers.get('Origin', '')

            if not api_key:
                return JsonResponse(
                    {'error': 'X-API-Key header is required'},
                    status=401
                )

            try:
                website = Website.objects.get(
                    api_key=api_key,
                    is_active=True
                )

                # validate origin domain
                if origin:
                    normalized_origin = origin.rstrip('/')
                    normalized_domain = website.domain.rstrip('/')
                    if normalized_origin != normalized_domain:
                        return JsonResponse(
                            {'error': 'Domain not authorized for this API key'},
                            status=403
                        )

                request.website = website

            except Website.DoesNotExist:
                return JsonResponse(
                    {'error': 'Invalid or inactive API key'},
                    status=401
                )

        return self.get_response(request)