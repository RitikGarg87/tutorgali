from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class PublishedPostManager(models.Manager):
    def published(self):
        return self.filter(
            is_published=True, published_at__lte=timezone.now(),
        )


class Post(models.Model):
    """
    A blog article — admin-authored only (no public submission flow; see
    blog/admin.py). Targets informational education queries ("CBSE Class 10
    syllabus", "how much does a home tutor cost") that the city/subject/
    board/grade landing pages in users/seo_views.py don't cover, and
    cross-links to those landing pages via the related_* hint fields below.
    """

    CATEGORY_CHOICES = (
        ('exam_tips', 'Exam Tips'),
        ('subject_guides', 'Subject Guides'),
        ('parenting', 'Parenting'),
        ('tutor_advice', 'Tutor Advice'),
    )

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    excerpt = models.CharField(
        max_length=300,
        help_text="Shown on the blog list page and used as the meta description if left blank there.",
    )
    # Plain admin-authored HTML, rendered with |safe in the template — the
    # project has no rich-text editor dependency today and only trusted
    # staff (via /admin/) can author posts, so this carries the same trust
    # boundary as the Django admin itself.
    body = models.TextField(help_text="HTML content, authored via the admin.")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    tags = models.CharField(max_length=255, blank=True, help_text="Comma-separated, free text.")
    meta_description = models.CharField(max_length=300, blank=True)
    # FileField (not ImageField) to match the project's other uploads
    # (Profile.education_certificate/id_proof in users/models.py) — avoids
    # adding Pillow as a new dependency just for image-dimension validation.
    featured_image = models.FileField(upload_to='blog/', blank=True, null=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    # Optional single-value hints an admin sets to drive deterministic
    # cross-linking to the matching SEO landing page (see
    # users/seo_views.py::_related_posts_for and the "Related" block in
    # users/templates/users/seo_city_landing.html). Left blank = no link.
    related_city = models.CharField(max_length=100, blank=True)
    related_subject = models.CharField(max_length=100, blank=True)
    related_board = models.CharField(max_length=100, blank=True)

    published_at = models.DateTimeField(default=timezone.now)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PublishedPostManager()

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:220]
        super().save(*args, **kwargs)

    @property
    def meta_description_or_excerpt(self):
        return self.meta_description or self.excerpt
