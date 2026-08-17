"""
SEO data & helpers for programmatic city / subject / board / grade landing
pages.

Single source of truth for:
  - Which city slugs resolve to a valid landing page (CITY_SLUG_MAP), derived
    from the existing CITIES_BY_STATE dropdown data in users/forms.py.
  - Which of those cities are "launch ready" for internal linking / sitemap
    inclusion (SEO_TARGET_CITIES) — a curated pan-India subset, not all ~700
    cities, to avoid flooding the site with thin/unlinked pages.
  - Which subjects (SUBJECTS) and exam boards (BOARDS) get dedicated
    "<facet> tuition in <city>" pages, and which grades (GRADE_SLUG_MAP) get
    "class <grade> tutor in <city>" pages — each kept as a single facet
    combined with city only (never subject+board+grade together, which would
    produce thousands of mostly-empty pages).
  - The indexability gate (MIN_TUTORS_FOR_INDEX / is_city_indexable) that
    keeps low-supply pages out of sitemap.xml and marked noindex until they
    have earned enough real tutor listings.
"""
from django.conf import settings
from django.utils.text import slugify

from .forms import CITIES_BY_STATE

# ── City slug map ────────────────────────────────────────────────────────────
# slug -> canonical display name, built from every city in the signup/
# onboarding dropdown data. Any of these resolve to a valid landing page
# (though only SEO_TARGET_CITIES are linked/indexed — see below).
CITY_SLUG_MAP: dict[str, str] = {
    slugify(city): city
    for cities in CITIES_BY_STATE.values()
    for city in cities
}
# Reverse lookup (city -> slug), for building URLs from a city name.
CITY_TO_SLUG: dict[str, str] = {city: slug for slug, city in CITY_SLUG_MAP.items()}

# ── Curated launch cities ────────────────────────────────────────────────────
# Pan-India shortlist (state capitals + 1-2 more tier-2/tier-3 cities per
# state/UT) used for internal linking, "nearby cities" suggestions, and
# sitemap eligibility. Kept deliberately small — growing this list is safe
# and cheap, but every entry here is treated as a page we're actively trying
# to rank, so it should reflect real target markets.
SEO_TARGET_CITIES: list[str] = [
    # Maharashtra
    'Mumbai', 'Pune', 'Nagpur', 'Nashik',
    # Delhi NCR / Haryana / UP
    'Delhi', 'New Delhi', 'Gurgaon', 'Noida', 'Ghaziabad',
    # Karnataka
    'Bengaluru', 'Mysuru',
    # Telangana / Andhra Pradesh
    'Hyderabad', 'Warangal', 'Visakhapatnam',
    # Tamil Nadu
    'Chennai', 'Coimbatore',
    # Gujarat
    'Ahmedabad', 'Surat', 'Vadodara',
    # Rajasthan
    'Jaipur', 'Udaipur', 'Jodhpur',
    # Uttar Pradesh
    'Lucknow', 'Kanpur', 'Varanasi', 'Agra',
    # Madhya Pradesh
    'Indore', 'Bhopal',
    # Bihar
    'Patna',
    # West Bengal
    'Kolkata', 'Siliguri',
    # Punjab / Chandigarh
    'Chandigarh', 'Ludhiana', 'Amritsar',
    # Kerala
    'Kochi', 'Thiruvananthapuram',
    # Odisha
    'Bhubaneswar',
    # Assam / Northeast
    'Guwahati',
    # Uttarakhand
    'Dehradun',
    # Jharkhand
    'Ranchi',
    # Chhattisgarh
    'Raipur',
    # Goa
    'Panaji',
    # Himachal Pradesh
    'Shimla',
]

# ── Subject-level pages ──────────────────────────────────────────────────────
# Short, high-intent subject list for "<subject> tuition in <city>" pages.
# Deliberately not the full subject list used in tutor onboarding — a full
# cross-product with SEO_TARGET_CITIES would produce ~1,400 mostly-thin pages.
SUBJECTS: list[str] = [
    'Mathematics', 'Science', 'English', 'Physics', 'Chemistry', 'Biology',
]
SUBJECT_SLUG_MAP: dict[str, str] = {slugify(s): s for s in SUBJECTS}
# Reverse lookup (subject -> slug).
SUBJECT_TO_SLUG: dict[str, str] = {s: slug for slug, s in SUBJECT_SLUG_MAP.items()}

# ── Exam board pages ─────────────────────────────────────────────────────────
# Matches TutorOnboardingForm.school_boards choices in users/forms.py exactly
# — the stored codes on Profile.school_boards double as the URL slugs here,
# so no separate slugify step is needed (unlike cities/subjects/grades).
BOARDS: list[tuple[str, str]] = [
    ('cbse', 'CBSE'), ('icse', 'ICSE'), ('state', 'State Board'),
    ('igcse', 'IGCSE'), ('ib', 'IB'), ('nios', 'NIOS'),
]
BOARD_SLUG_MAP: dict[str, str] = dict(BOARDS)  # slug (= stored code) -> display label

# ── Grade-level pages ────────────────────────────────────────────────────────
# Human-friendly URL slugs ("10", "nursery-to-5") mapped to the stored code
# and display label. Kept 1:1 with TutorGradeRate.GRADE_CHOICES in
# users/models.py — update both together if grades ever change.
GRADE_SLUG_MAP: dict[str, tuple[str, str]] = {
    'nursery-to-5': ('nursery_to_5', 'Nursery to 5th'),
    '6': ('grade_6', '6th'), '7': ('grade_7', '7th'), '8': ('grade_8', '8th'),
    '9': ('grade_9', '9th'), '10': ('grade_10', '10th'),
    '11': ('grade_11', '11th'), '12': ('grade_12', '12th'),
}
# Reverse lookup (stored grade code -> URL slug), for sitemap/internal links.
GRADE_CODE_TO_SLUG: dict[str, str] = {
    code: slug for slug, (code, _label) in GRADE_SLUG_MAP.items()
}

# ── Indexability gate ────────────────────────────────────────────────────────
# A city page only gets indexed (added to sitemap.xml, robots="index,follow")
# once it's both a curated target city AND has enough real tutor listings to
# not look like thin content. Configurable via .env (settings.MIN_TUTORS_FOR_INDEX)
# so it can be tuned as the marketplace grows without a code change.
MIN_TUTORS_FOR_INDEX: int = settings.MIN_TUTORS_FOR_INDEX

# city -> state, used to prefer same-state suggestions in nearby_cities()
_CITY_TO_STATE: dict[str, str] = {
    city: state for state, cities in CITIES_BY_STATE.items() for city in cities
}


def is_city_indexable(city: str, tutor_count: int) -> bool:
    """Whether a city (landing or subject+city) page should be indexed."""
    return city in SEO_TARGET_CITIES and tutor_count >= MIN_TUTORS_FOR_INDEX


def nearby_cities(city: str, limit: int = 8) -> list[str]:
    """Other curated target cities to internally link to from a city page.

    Same-state cities are preferred (more relevant for "near me" style
    internal linking), padded out with other target cities if needed.
    """
    others = [c for c in SEO_TARGET_CITIES if c != city]
    state = _CITY_TO_STATE.get(city)
    same_state = [c for c in others if _CITY_TO_STATE.get(c) == state] if state else []
    rest = [c for c in others if c not in same_state]
    return (same_state + rest)[:limit]
