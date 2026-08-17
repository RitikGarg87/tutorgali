from django.conf import settings


def seo_defaults(request):
    """Makes the canonical site domain/URL available in every template,
    for building absolute canonical/OG/sitemap-referencing URLs."""
    return {
        'SITE_DOMAIN': settings.SITE_DOMAIN,
        'SITE_URL': settings.SITE_URL,
    }
