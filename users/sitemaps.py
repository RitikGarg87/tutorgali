"""
sitemap.xml definitions.

Only "static" marketing/legal pages, approved tutor profiles, and SEO
city / subject+city / board+city / grade+city landing pages that have at
least one verified tutor are included.

Thin-content guard: with a large city list, a full cross-product would emit
~13k URLs, most pointing at empty pages — Google treats mass near-duplicate
empty pages as thin/doorway content. So the landing-page sitemaps below only
advertise combinations that actually have a verified tutor (the same "who
counts as a listed tutor" rule as the landing pages themselves, via
_base_tutor_queryset). Empty pages still resolve and are crawlable, but they
mark themselves `noindex` (see seo_views._render_landing) and stay out of the
sitemap. As tutors join, their city/subject/board/grade pages enter the
sitemap automatically — no manual curation.

The inventory (which cities/facets have tutors) is computed once per sitemap
request via a single pass over approved tutors (see _TutorInventory), not a
per-URL query, to keep sitemap generation cheap.
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils.text import slugify

from . import seo_data
from .models import Profile
from .views import _base_tutor_queryset


def _split_csv(value):
    """Split a comma-separated field (subjects / school_boards) into a clean
    lowercase set of tokens. Mirrors how filter_tutors matches these fields
    (case-insensitive substring), but exact-token here since we control the
    facet vocabulary."""
    if not value:
        return set()
    return {part.strip().lower() for part in value.split(',') if part.strip()}


class _TutorInventory:
    """Single pass over the approved-tutor pool, recording which cities and
    (city, facet) combinations actually have a tutor. The landing-page
    sitemaps below iterate these sets directly, so they emit only URLs backed
    by a real tutor — O(existing combos), never the full city × facet
    cross-product.

    Facet values are stored as their URL slug (city -> CITY_TO_SLUG, subject
    -> SUBJECT_TO_SLUG, grade code -> GRADE_CODE_TO_SLUG, board code == slug),
    so sitemap `location()` can reverse() directly without re-mapping. Combos
    whose city/facet isn't in the SEO slug vocabulary are dropped (no landing
    page exists for them)."""

    def __init__(self):
        self.city_slugs: set[str] = set()
        self.subject_pairs: set[tuple[str, str]] = set()  # (subject_slug, city_slug)
        self.board_pairs: set[tuple[str, str]] = set()    # (board_slug, city_slug)
        self.grade_pairs: set[tuple[str, str]] = set()    # (grade_slug, city_slug)

        # _base_tutor_queryset() prefetches grade_rates, so gr loop is not N+1.
        for tutor in _base_tutor_queryset():
            city_slug = self._city_slug(tutor.city)
            if not city_slug:
                continue
            self.city_slugs.add(city_slug)

            for board in _split_csv(tutor.school_boards):
                if board in seo_data.BOARD_SLUG_MAP:
                    self.board_pairs.add((board, city_slug))

            for gr in tutor.grade_rates.all():
                grade_slug = seo_data.GRADE_CODE_TO_SLUG.get(gr.grade)
                if grade_slug:
                    self.grade_pairs.add((grade_slug, city_slug))
                for subject in _split_csv(gr.subjects):
                    subject_slug = self._subject_slug(subject)
                    if subject_slug:
                        self.subject_pairs.add((subject_slug, city_slug))

    @staticmethod
    def _city_slug(city):
        if not city:
            return None
        return seo_data.CITY_TO_SLUG.get(city.strip())

    @staticmethod
    def _subject_slug(subject):
        # Tutor subjects are free-text-ish; match against the SEO vocabulary
        # by slug (SUBJECT_SLUG_MAP keys are slugified subject names).
        slug = slugify(subject)
        return slug if slug in seo_data.SUBJECT_SLUG_MAP else None


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


class CityLandingSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return sorted(_TutorInventory().city_slugs)

    def location(self, city_slug):
        return reverse('seo_city_landing', args=[city_slug])


class _FacetCityLandingSitemap(Sitemap):
    """
    Shared base for every "<facet>+city" sitemap (subject, board, grade).
    Subclasses set `pairs_attr` (the _TutorInventory attribute holding the
    (facet_slug, city_slug) pairs) and `url_name`. Items are the pairs
    themselves, so only combinations backed by a verified tutor are emitted.
    """
    changefreq = 'weekly'
    priority = 0.7
    pairs_attr: str = ''
    url_name: str = ''

    def items(self):
        return sorted(getattr(_TutorInventory(), self.pairs_attr))

    def location(self, item):
        facet_slug, city_slug = item
        return reverse(self.url_name, args=[facet_slug, city_slug])


class SubjectCityLandingSitemap(_FacetCityLandingSitemap):
    pairs_attr = 'subject_pairs'
    url_name = 'seo_facet_city_landing'


class BoardCityLandingSitemap(_FacetCityLandingSitemap):
    pairs_attr = 'board_pairs'
    url_name = 'seo_facet_city_landing'


class GradeCityLandingSitemap(_FacetCityLandingSitemap):
    pairs_attr = 'grade_pairs'
    url_name = 'seo_grade_city_landing'
