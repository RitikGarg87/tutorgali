from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include

from blog.sitemaps import BlogPostSitemap
from users.sitemaps import (
    StaticViewSitemap, TutorProfileSitemap,
    CityLandingSitemap, SubjectCityLandingSitemap,
    BoardCityLandingSitemap, GradeCityLandingSitemap,
)

sitemaps = {
    'static': StaticViewSitemap,
    'tutors': TutorProfileSitemap,
    'cities': CityLandingSitemap,
    'subjects': SubjectCityLandingSitemap,
    'boards': BoardCityLandingSitemap,
    'grades': GradeCityLandingSitemap,
    'blog': BlogPostSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('blog/', include('blog.urls')),
    path('', include('users.urls')),
]
