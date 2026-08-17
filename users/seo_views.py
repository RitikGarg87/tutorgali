"""
Views for programmatic SEO landing pages — city, subject+city, board+city,
and grade+city ("home tuition in <city>", "<subject> tuition in <city>",
"cbse tuition in <city>", "class 10 tutor in <city>") — plus crawler-facing
infra (robots.txt).

Every landing page is "city + at most one facet" (subject, board, or grade —
never combined) to keep the page count bounded; see users/seo_data.py for the
slug data and the indexability gate these views rely on. Kept separate from
users/views.py since these are pure SEO/content routes with no auth, forms,
or booking logic.
"""
from django.conf import settings
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render

from blog.models import Post

from . import seo_data
from .views import filter_tutors

PAGE_SIZE = 20

# Generic FAQ content reused across every landing page. Deliberately
# city-agnostic copy with {city} interpolated at render time, rather than
# per-city hand-written content.
_BASE_FAQS = [
    (
        "How do I find a good home tutor in {city}?",
        "Search TutorGali by grade, subject, and teaching mode to see verified "
        "tutors {in_city}. Every tutor profile shows experience, qualifications, "
        "rates, and student reviews so you can compare before you connect.",
    ),
    (
        "Are TutorGali tutors {in_city} verified?",
        "Yes. Tutors go through a manual verification process — including "
        "qualification and ID checks — before their profile is approved and "
        "shown to students.",
    ),
    (
        "How much does home tuition cost {in_city}?",
        "Rates vary by tutor, subject, and teaching mode (online, at your home, "
        "or at the tutor's home). Each tutor sets their own hourly rate, shown "
        "upfront on their profile — there are no hidden platform fees.",
    ),
    (
        "Is it free to contact a tutor {in_city} on TutorGali?",
        "Yes, signing up as a student is free. Once a tutor accepts your "
        "booking request you can view their contact details and connect "
        "directly.",
    ),
]

# One extra, facet-specific FAQ row prepended for subject/board/grade pages.
# facet_type -> a (question, answer) template using {city} and {label}.
_FACET_FAQS = {
    'subject': (
        "Do TutorGali tutors in {city} teach {label}?",
        "Yes — use the filters below to see tutors in {city} who teach {label}, "
        "along with their grade coverage, teaching mode, and rates.",
    ),
    'board': (
        "Are there {label} tutors in {city}?",
        "Yes — tutors on TutorGali list which boards they teach, including "
        "{label}. Check each tutor's profile for board-specific experience "
        "before you connect.",
    ),
    'grade': (
        "Are there tutors for {label} in {city}?",
        "Yes — filter by grade below to see tutors in {city} who teach {label}, "
        "along with their subjects, teaching mode, and rates.",
    ),
}


def _faqs_for(city, facet_type=None, facet_label=None):
    in_city = f"in {city}"
    faqs = [
        {'question': q.format(city=city, in_city=in_city),
         'answer': a.format(city=city, in_city=in_city)}
        for q, a in _BASE_FAQS
    ]
    if facet_type:
        q, a = _FACET_FAQS[facet_type]
        faqs.insert(0, {
            'question': q.format(city=city, label=facet_label),
            'answer': a.format(city=city, label=facet_label),
        })
    return faqs


def _render_landing(request, city, *, subject=None, board_label=None,
                     board_code=None, grade_label=None, grade_code=None):
    """
    Shared renderer for every SEO landing page. Exactly one of
    subject / board_label / grade_label is expected to be set — a page is
    "city + at most one facet", never a combination (see module docstring).
    """
    tutors = filter_tutors(city, subject=subject, board=board_code, grade=grade_code)
    paginator = Paginator(tutors, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))
    tutor_count = paginator.count

    is_indexable = seo_data.is_city_indexable(city, tutor_count)

    if subject:
        facet_type, facet_label = 'subject', subject
    elif board_label:
        facet_type, facet_label = 'board', board_label
    elif grade_label:
        facet_type, facet_label = 'grade', grade_label
    else:
        facet_type, facet_label = None, None

    # "Mathematics Tuition in Pune" / "CBSE Tuition in Pune" /
    # "Home Tuition in Pune" — the single phrase every title/H1/breadcrumb
    # variant below is built from, so each facet type only needs one line.
    topic = f"{facet_label} Tuition" if facet_type in ('subject', 'board') else "Home Tuition"
    who = f"{facet_label} tutor" if facet_type in ('subject', 'board') else "tutor"
    # "Class 10th" reads naturally; "Class Nursery to 5th" doesn't, so only
    # prefix "Class" when the grade label is a numbered grade.
    grade_phrase = f"Class {grade_label}" if grade_label and grade_label[0].isdigit() else grade_label

    breadcrumb_label = (
        f"{grade_phrase} Tutors in {city}" if facet_type == 'grade' else f"{topic} in {city}"
    )
    title = f"{breadcrumb_label} | Find a Tutor Near You – TutorGali"
    if facet_type == 'grade':
        page_h1 = f"{grade_phrase} Home Tutors in {city}"
    elif facet_type:
        page_h1 = f"{facet_label} Home Tutors in {city}"
    else:
        page_h1 = f"Find the Best Home Tutors in {city}"

    if tutor_count:
        meta_description = (
            f"Find {tutor_count} verified {who}s in {city} offering home & online "
            f"tuition. Compare rates, read reviews, and connect with tutors near you."
        )
    else:
        meta_description = (
            f"Be the first verified {who} to join TutorGali in {city}. Students in "
            f"{city} are searching for {topic.lower()} right now."
        )

    nearby = seo_data.nearby_cities(city) if is_indexable else []
    nearby_cities = [
        {'name': c, 'slug': seo_data.CITY_TO_SLUG[c]} for c in nearby
    ]

    context = {
        'city': city,
        'subject': subject,
        'board_label': board_label,
        'grade_label': grade_label,
        'title': title,
        'page_h1': page_h1,
        'breadcrumb_label': breadcrumb_label,
        'meta_description': meta_description,
        'results': page_obj,
        'tutor_count': tutor_count,
        'is_indexable': is_indexable,
        'nearby_cities': nearby_cities,
        'faqs': _faqs_for(city, facet_type, facet_label),
        'related_posts': _related_posts_for(facet_type),
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
        'canonical_url': request.build_absolute_uri(request.path),
    }
    return render(request, 'users/seo_city_landing.html', context)


# facet type -> blog category most relevant to link from a landing page.
_FACET_TO_BLOG_CATEGORY = {
    'subject': 'subject_guides',
    'board': 'exam_tips',
    'grade': 'exam_tips',
}


def _related_posts_for(facet_type):
    """Up to 2 published blog posts to cross-link from a landing page."""
    category = _FACET_TO_BLOG_CATEGORY.get(facet_type)
    posts = Post.objects.published()
    if category:
        posts = posts.filter(category=category)
    return list(posts[:2])


def seo_city_landing(request, city_slug):
    """'Home tuition in <city>' landing page — see users/seo_data.py for the
    slug -> city mapping and the indexability rules."""
    city = seo_data.CITY_SLUG_MAP.get(city_slug)
    if not city:
        raise Http404("Unknown city")
    return _render_landing(request, city)


def seo_facet_city_landing(request, facet_slug, city_slug):
    """'<subject|board> tuition in <city>' landing page — subject and board
    share this one URL/view since both use the same URL shape; only
    generated for the curated SEO_TARGET_CITIES."""
    city = seo_data.CITY_SLUG_MAP.get(city_slug)
    if not city or city not in seo_data.SEO_TARGET_CITIES:
        raise Http404("Unknown city")

    if facet_slug in seo_data.SUBJECT_SLUG_MAP:
        return _render_landing(request, city, subject=seo_data.SUBJECT_SLUG_MAP[facet_slug])
    if facet_slug in seo_data.BOARD_SLUG_MAP:
        return _render_landing(
            request, city,
            board_label=seo_data.BOARD_SLUG_MAP[facet_slug], board_code=facet_slug,
        )
    raise Http404("Unknown subject or board")


def seo_grade_city_landing(request, grade_slug, city_slug):
    """'Class <grade> tutor in <city>' landing page — only generated for the
    curated SEO_TARGET_CITIES."""
    city = seo_data.CITY_SLUG_MAP.get(city_slug)
    grade = seo_data.GRADE_SLUG_MAP.get(grade_slug)
    if not city or not grade or city not in seo_data.SEO_TARGET_CITIES:
        raise Http404("Unknown city or grade")
    grade_code, grade_label = grade
    return _render_landing(request, city, grade_label=grade_label, grade_code=grade_code)


def seo_robots_txt(request):
    return render(
        request,
        'users/robots.txt',
        {'SITE_URL': settings.SITE_URL},
        content_type='text/plain',
    )

