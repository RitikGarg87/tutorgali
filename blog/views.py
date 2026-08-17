from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from users import seo_data

from .models import Post

PAGE_SIZE = 12


def _related_landing(post):
    """
    Resolve a post's optional related_city/related_subject/related_board
    hints (set by the admin, see blog/admin.py) into a URL + human label for
    the "Find Tutors" CTA on the post detail page. Returns (url, label) or
    (None, None) if the hints don't resolve to a known landing page.
    """
    city_slug = seo_data.CITY_TO_SLUG.get(post.related_city)
    if not city_slug:
        return None, None

    if post.related_subject and post.related_subject in seo_data.SUBJECT_TO_SLUG:
        facet_slug = seo_data.SUBJECT_TO_SLUG[post.related_subject]
        label = f"{post.related_subject} tutors in {post.related_city}"
        return reverse('seo_facet_city_landing', args=[facet_slug, city_slug]), label

    if post.related_board and post.related_board in seo_data.BOARD_SLUG_MAP:
        label = f"{seo_data.BOARD_SLUG_MAP[post.related_board]} tutors in {post.related_city}"
        return reverse('seo_facet_city_landing', args=[post.related_board, city_slug]), label

    label = f"tutors in {post.related_city}"
    return reverse('seo_city_landing', args=[city_slug]), label


def blog_list(request, category=None):
    posts = Post.objects.published()
    category_label = None
    if category:
        posts = posts.filter(category=category)
        category_label = dict(Post.CATEGORY_CHOICES).get(category)
        if category_label is None:
            posts = posts.none()

    paginator = Paginator(posts, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))

    title = f"{category_label} Articles" if category_label else "Blog"
    context = {
        'title': f"{title} | TutorGali",
        'meta_description': (
            f"TutorGali's {category_label} articles — practical guides for students, "
            f"parents, and tutors." if category_label else
            "Exam tips, subject guides, and tutoring advice from TutorGali."
        ),
        'canonical_url': request.build_absolute_uri(request.path),
        'posts': page_obj,
        'category': category,
        'category_label': category_label,
        'categories': Post.CATEGORY_CHOICES,
    }
    return render(request, 'blog/blog_list.html', context)


def blog_detail(request, slug):
    posts = Post.objects if request.user.is_staff else Post.objects.published()
    post = get_object_or_404(posts, slug=slug)
    related_posts = (
        Post.objects.published()
        .filter(category=post.category)
        .exclude(pk=post.pk)[:3]
    )

    related_landing_url, related_landing_label = _related_landing(post)

    context = {
        'post': post,
        'title': f"{post.title} | TutorGali Blog",
        'meta_description': post.meta_description_or_excerpt,
        'canonical_url': request.build_absolute_uri(request.path),
        'related_posts': related_posts,
        'related_landing_url': related_landing_url,
        'related_landing_label': related_landing_label,
    }
    return render(request, 'blog/blog_detail.html', context)
