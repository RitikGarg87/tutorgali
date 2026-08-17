from django.urls import path

from . import views
from .feeds import LatestPostsFeed

urlpatterns = [
    path('', views.blog_list, name='blog_list'),
    path('rss/', LatestPostsFeed(), name='blog_rss'),
    path('category/<slug:category>/', views.blog_list, name='blog_category'),
    path('<slug:slug>/', views.blog_detail, name='blog_detail'),
]
