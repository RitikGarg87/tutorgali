from django.contrib.syndication.views import Feed
from django.urls import reverse

from .models import Post


class LatestPostsFeed(Feed):
    title = "TutorGali Blog"
    description = "Exam tips, subject guides, and tutoring advice from TutorGali."

    def link(self):
        return reverse('blog_list')

    def items(self):
        return Post.objects.published()[:20]

    def item_title(self, post):
        return post.title

    def item_description(self, post):
        return post.excerpt

    def item_link(self, post):
        return reverse('blog_detail', args=[post.slug])

    def item_pubdate(self, post):
        return post.published_at
