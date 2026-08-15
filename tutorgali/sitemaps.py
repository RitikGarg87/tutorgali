from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"

    def items(self):
        return [
            "register",
            "browse_tutors",
            "search_tutors",
            "subscription_plans",
            "privacy_policy",
            "terms_conditions",
            "refund_policy",
            "contact_us",
        ]

    def location(self, item):
        return reverse(item)
