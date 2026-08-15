from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"

    def items(self):
        return [
            "home",
            "public_search_tutors",
            "register",
            "subscription_plans",
            "privacy_policy",
            "terms_conditions",
            "refund_policy",
            "contact_us",
        ]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        priorities = {
            "home": 1.0,
            "public_search_tutors": 0.9,
            "register": 0.7,
            "subscription_plans": 0.6,
            "privacy_policy": 0.3,
            "terms_conditions": 0.3,
            "refund_policy": 0.3,
            "contact_us": 0.5,
        }
        return priorities.get(item, 0.5)

    def changefreq(self, item):
        frequencies = {
            "home": "daily",
            "public_search_tutors": "daily",
        }
        return frequencies.get(item, "monthly")