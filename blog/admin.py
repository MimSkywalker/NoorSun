from django.contrib import admin

from .models import Post, PostCategory, PostComment, Tag


class PostCommentInline(admin.TabularInline):
    model = PostComment
    extra = 0
    fields = ('display_name', 'text', 'is_approved', 'admin_reply')
    readonly_fields = ('display_name', 'text')

    def display_name(self, obj):
        return obj.display_name


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'title_en', 'category', 'author', 'status', 'published_at')
    list_filter = ('status', 'category', 'tags')
    search_fields = ('title', 'title_en', 'excerpt')
    autocomplete_fields = ('category', 'author')
    filter_horizontal = ('tags',)
    inlines = [PostCommentInline]

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)


@admin.register(PostCategory)
class PostCategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'title_en')
    search_fields = ('title', 'title_en')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('title', 'title_en')
    search_fields = ('title', 'title_en')


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'display_name', 'is_approved', 'created_at')
    list_filter = ('is_approved',)
    search_fields = ('post__title', 'text')
    readonly_fields = ('post', 'user', 'guest_name', 'text', 'created_at')
    actions = ['approve_comments']

    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)
    approve_comments.short_description = "تأیید نظرات انتخاب‌شده"