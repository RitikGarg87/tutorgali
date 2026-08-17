"""
sitemap.xml definitions.

Only "static" marketing/legal pages, approved tutor profiles, and SEO
city / subject+city / board+city / grade+city landing pages that have
passed the indexability gate (users.seo_data.is_city_indexable) are
included — thin/empty landing pages are intentionally left out of the
sitemap until they earn real tutor listings (see the SEO plan context in
users/seo_data.py).
"""
from django.contrib.sitemaps import Sitemap
from django.core.cache import cache
from django.db.models import Count
from django.urls import reverse

from . import seo_data
from .models import Profile

_TUTOR_COUNTS_CACHE_KEY = 'seo:tutor_counts_by_city'
_TUTOR_COUNTS_CACHE_TTL = 60  # seconds — long enough to dedupe the two
# sitemap classes' queries within a single sitemap.xml crawl, short enough
# that a newly-approved tutor's city flips to indexed within a minute.


class StaticViewSitemap(Sitemap):
    priority = 0.6
    changefreq = 'monthly'

    def items(self):
        return [
            'home', 'public_search_tutors', 'privacy_policy',
            'terms_conditions', 'refund_policy', 'contact_us',
        ]

    def location(self, item):
        return reverse(item)


class TutorProfileSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        # order_by('id'): Profile has no default ordering — required for
        # stable pagination (Sitemap paginates items() internally).
        return Profile.objects.filter(
            role='tutor', profile_completed=True, verification_status='approved',
        ).order_by('id')

    def location(self, tutor):
        return reverse('tutor_public_profile', args=[tutor.id])


def _tutor_counts_by_city(subject=None, board=None, grade=None):
    """{city: approved_tutor_count} for the curated SEO_TARGET_CITIES only,
    optionally narrowed to one facet — mirrors users.views.filter_tutors()
    so a sitemap entry only ever exists for a page that would actually
    render as indexable (see is_city_indexable). Briefly cached since
    sitemap.xml instantiates each Sitemap subclass independently per
    request, and would otherwise re-run the same query per facet value.
    """
    cache_key = f'{_TUTOR_COUNTS_CACHE_KEY}:{subject or ""}:{board or ""}:{grade or ""}'
    counts = cache.get(cache_key)
    if counts is not None:
        return counts
    qs = Profile.objects.filter(
        role='tutor', profile_completed=True, verification_status='approved',
        city__in=seo_data.SEO_TARGET_CITIES,
    )
    if subject:
        qs = qs.filter(grade_rates__subjects__icontains=subject)
    if board:
        qs = qs.filter(school_boards__icontains=board)
    if grade:
        qs = qs.filter(grade_rates__grade=grade)
    rows = qs.values('city').annotate(count=Count('id', distinct=True))
    counts = {row['city']: row['count'] for row in rows}
    cache.set(cache_key, counts, _TUTOR_COUNTS_CACHE_TTL)
    return counts


def _indexable_cities():
    counts = _tutor_counts_by_city()
    return [
        city for city in seo_data.SEO_TARGET_CITIES
        if seo_data.is_city_indexable(city, counts.get(city, 0))
    ]


class CityLandingSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return _indexable_cities()

    def location(self, city):
        return reverse('seo_city_landing', args=[seo_data.CITY_TO_SLUG[city]])


class _FacetCityLandingSitemap(Sitemap):
    """
    Shared base for every "<facet>+city" sitemap (subject, board, grade).
    Subclasses set `facet_kwarg` (which filter_tutors()/_tutor_counts_by_city
    kwarg this facet type uses: 'subject' | 'board' | 'grade'), `facet_values`
    (list of (url_slug, filter_value) pairs), and `url_name`. A (facet, city)
    pair only appears here if that *specific* facet+city combination is
    indexable — not just the city overall — so the sitemap never lists a
    page that the page itself would render as noindex.
    """
    changefreq = 'weekly'
    priority = 0.7
    facet_kwarg: str = ''
    facet_values: list[tuple[str, str]] = []
    url_name: str = ''

    def items(self):
        result = []
        for slug, value in self.facet_values:
            counts = _tutor_counts_by_city(**{self.facet_kwarg: value})
            result += [
                (slug, city) for city in seo_data.SEO_TARGET_CITIES
                if seo_data.is_city_indexable(city, counts.get(city, 0))
            ]
        return result

    def location(self, item):
        facet_slug, city = item
        return reverse(self.url_name, args=[facet_slug, seo_data.CITY_TO_SLUG[city]])


class SubjectCityLandingSitemap(_FacetCityLandingSitemap):
    facet_kwarg = 'subject'
    facet_values = list(seo_data.SUBJECT_SLUG_MAP.items())  # (slug, "Mathematics")
    url_name = 'seo_facet_city_landing'


class BoardCityLandingSitemap(_FacetCityLandingSitemap):
    facet_kwarg = 'board'
    facet_values = [(code, code) for code in seo_data.BOARD_SLUG_MAP]  # slug == stored code
    url_name = 'seo_facet_city_landing'


class GradeCityLandingSitemap(_FacetCityLandingSitemap):
    facet_kwarg = 'grade'
    facet_values = [(slug, code) for slug, (code, _label) in seo_data.GRADE_SLUG_MAP.items()]
    url_name = 'seo_grade_city_landing'
