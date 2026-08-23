"""B-24. Django admin — every model registered with list_display, search & filters."""
from django.contrib import admin

from .models import (
    Category,
    Comment,
    ContactMessage,
    Education,
    Experience,
    Post,
    PostLike,
    Profile,
    Project,
    Skill,
    Tag,
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "headline", "email", "is_available_for_hire")
    search_fields = ("full_name", "headline", "email")


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "proficiency", "is_featured", "display_order")
    list_filter = ("category", "is_featured")
    search_fields = ("name",)
    list_editable = ("proficiency", "is_featured", "display_order")


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ("role", "company", "employment_type", "start_date", "end_date", "is_current")
    list_filter = ("employment_type", "is_current")
    search_fields = ("role", "company", "description")


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ("degree", "institution", "field_of_study", "start_year", "end_year")
    list_filter = ("field_of_study",)
    search_fields = ("degree", "institution", "field_of_study")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_featured", "completed_date", "display_order")
    list_filter = ("category", "is_featured")
    search_fields = ("title", "summary", "description")
    prepopulated_fields = {"slug": ("title",)} # noqa: RUF012
    filter_horizontal = ("tech_stack",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "description")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)} # noqa: RUF012


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)} # noqa: RUF012


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "is_featured", "views_count", "published_at")
    list_filter = ("status", "is_featured", "category", "tags")
    search_fields = ("title", "excerpt", "content")
    prepopulated_fields = {"slug": ("title",)} # noqa: RUF012
    filter_horizontal = ("tags",)
    readonly_fields = ("views_count", "reading_time", "published_at")


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ("post", "visitor_id", "ip_address", "created_at")
    list_filter = ("created_at",)
    search_fields = ("visitor_id", "post__title")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("name", "post", "is_approved", "parent", "created_at")
    list_filter = ("is_approved", "created_at")
    search_fields = ("name", "email", "content")
    list_editable = ("is_approved",)
    actions = ("approve_comments")

    @admin.action(description="Approve selected comments")
    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "name", "email", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("subject", "name", "email", "message")
