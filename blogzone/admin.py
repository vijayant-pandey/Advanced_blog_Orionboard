from django.contrib import admin
from .models import Post, Like, Comment, ViewEvent, Category, Tag, PostSection, FaqItem, ContactMessage, Video

# Show sections inline in Post admin
class PostSectionInline(admin.TabularInline):
    model = PostSection
    extra = 0

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "status", "is_featured" ,"view_count", "edit_count", "published_at", "created_at")
    list_filter = ("status", "author", "is_featured" ,"created_at", "category")
    list_editable = ("is_featured",)  # lets you toggle directly from the list view
    search_fields = ("title", "content", "quote", "author__username")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "published_at"
    ordering = ("-published_at",)
    inlines = [PostSectionInline]

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "created_at")
    list_filter = ("created_at", "post", "user")


@admin.action(description="Mark selected comments as approved")
def approve_comments(modeladmin, request, queryset):
    queryset.update(status=Comment.STATUS_APPROVED)


@admin.action(description="Mark selected comments as rejected")
def reject_comments(modeladmin, request, queryset):
    queryset.update(status=Comment.STATUS_REJECTED)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "status", "parent", "created_at")
    list_filter = ("status", "created_at", "post")
    search_fields = ("content", "user__username", "post__title")
    actions = [approve_comments, reject_comments]

    def short_content(self, obj):
        return (obj.content[:40] + "...") if len(obj.content) > 40 else obj.content

    short_content.short_description = "Content"

@admin.register(ViewEvent)
class ViewEventAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "ip_address", "country", "city", "created_at")
    list_filter = ("post", "user", "created_at")
    search_fields = ("ip_address", "user_agent", "post__title", "user__username")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

@admin.register(FaqItem)
class FaqItemAdmin(admin.ModelAdmin):
    list_display = ("question", "is_active", "display_order")
    list_filter = ("is_active",)
    list_editable = ("is_active", "display_order")
    search_fields = ("question", "answer")
    ordering = ("display_order", "id")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "phone" ,"subject", "created_at", "is_resolved")
    list_filter = ("is_resolved", "created_at")
    search_fields = ("first_name", "last_name", "email", "subject", "message")
    readonly_fields = ("first_name", "last_name", "email", "phone", "subject", "message", "created_at")


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("title", "youtube_url" ,"is_active", "display_order", "created_at")
    list_filter = ("is_active", "created_at")
    list_editable = ("is_active", "display_order")
    search_fields = ("title", "youtube_url")
    ordering = ("display_order", "-created_at")