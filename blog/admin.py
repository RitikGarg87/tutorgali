from django.contrib import admin

from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_published', 'published_at', 'author')
    list_filter = ('category', 'is_published')
    search_fields = ('title', 'excerpt', 'tags')
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'category', 'author')}),
        ('Content', {'fields': ('excerpt', 'body', 'featured_image')}),
        ('SEO', {'fields': ('meta_description', 'tags')}),
        ('Cross-linking (optional)', {
            'fields': ('related_city', 'related_subject', 'related_board'),
            'description': (
                "Set at most the fields that apply — used to show a "
                "\"Find tutors\" CTA linking to the matching landing page."
            ),
        }),
        ('Publishing', {'fields': ('is_published', 'published_at')}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)
