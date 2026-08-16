from django.contrib import admin
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from .sitemaps import StaticViewSitemap
from django.http import HttpResponse
from users.views import razorpay_webhook

sitemaps = {
    "static": StaticViewSitemap,
}

def robots_txt(request):
    content = """User-agent: *
    Allow: /
    Sitemap: https://tutorgali.in/sitemap.xml
    """
    return HttpResponse(content, content_type="text/plain")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('webhooks/razorpay/',razorpay_webhook,name='razorpay_webhook'),
    path(
    "sitemap.xml",
    sitemap,
    {
        "sitemaps": sitemaps,
        "template_name": "users/sitemap.xml",
    },
    name="sitemap",
    ),
    path('', include('users.urls')),  
]
