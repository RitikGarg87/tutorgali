from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Post


class BlogPostSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.6

    def items(self):
        return Post.objects.published()

    def lastmod(self, post):
        return post.updated_at

    def location(self, post):
        return reverse('blog_detail', args=[post.slug])
