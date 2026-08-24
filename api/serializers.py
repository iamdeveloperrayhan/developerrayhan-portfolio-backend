"""
DRF serializers for DevFolio.

Serializer-level validation (B-21) lives here with clear, field-scoped error
messages so the React forms can show them under the right field (F-13).
"""
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import (
    Category,
    Comment,
    ContactMessage,
    Education,
    Experience,
    Post,
    Profile,
    Project,
    Skill,
    Tag,
)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "is_superuser")


class LoginSerializer(TokenObtainPairSerializer):
    """Adds the user object to the token response (B-14 login contract)."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = (
            "id", "full_name", "headline", "bio", "email", "phone", "location",
            "avatar", "resume", "github_url", "linkedin_url", "x_url",
            "website_url", "years_of_experience", "is_available_for_hire",
            "created_at", "updated_at",
        )


# ---------------------------------------------------------------------------
# Skill
# ---------------------------------------------------------------------------
class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = (
            "id", "name", "category", "proficiency", "icon", "icon_image",
            "display_order", "is_featured", "created_at", "updated_at",
        )

    def validate_proficiency(self, value):
        if not 1 <= value <= 100:
            raise serializers.ValidationError("Proficiency must be between 1 and 100.")
        return value


class SkillMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ("id", "name", "category", "icon", "icon_image")


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------
class ExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experience
        fields = (
            "id", "company", "role", "employment_type", "location",
            "start_date", "end_date", "is_current", "description",
            "company_url", "display_order", "created_at", "updated_at",
        )

    def validate(self, attrs):
        # Merge with existing instance values on PATCH.
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        is_current = attrs.get(
            "is_current", getattr(self.instance, "is_current", False)
        )

        if start and start > timezone.now().date():
            raise serializers.ValidationError(
                {"start_date": "Start date cannot be in the future."}
            )
        if is_current:
            if end:
                raise serializers.ValidationError(
                    {"end_date": "A current role must not have an end date."}
                )
        else:
            if not end:
                raise serializers.ValidationError(
                    {"end_date": "End date is required unless this is your current role."}
                )
            if start and end and end <= start:
                raise serializers.ValidationError(
                    {"end_date": "End date must be after the start date."}
                )
        return attrs


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------
class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = (
            "id", "institution", "degree", "field_of_study", "start_year",
            "end_year", "grade", "description", "display_order",
            "created_at", "updated_at",
        )

    def validate(self, attrs):
        start = attrs.get("start_year", getattr(self.instance, "start_year", None))
        end = attrs.get("end_year", getattr(self.instance, "end_year", None))
        if start and end and end < start:
            raise serializers.ValidationError(
                {"end_year": "End year cannot be before the start year."}
            )
        return attrs


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------
class ProjectSerializer(serializers.ModelSerializer):
    tech_stack = SkillMiniSerializer(many=True, read_only=True)
    tech_stack_ids = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, queryset=Skill.objects.all(),
        source="tech_stack", required=False,
    )

    class Meta:
        model = Project
        fields = (
            "id", "title", "slug", "summary", "description", "cover_image",
            "tech_stack", "tech_stack_ids", "category", "live_url",
            "github_url", "is_featured", "completed_date", "display_order",
            "created_at", "updated_at",
        )
        read_only_fields = ("slug",)

    def validate(self, attrs):
        live = attrs.get("live_url", getattr(self.instance, "live_url", ""))
        github = attrs.get("github_url", getattr(self.instance, "github_url", ""))
        if not live and not github:
            raise serializers.ValidationError(
                "Provide at least one of a live URL or a GitHub URL."
            )
        return attrs


# ---------------------------------------------------------------------------
# Blog: Category / Tag
# ---------------------------------------------------------------------------
class CategorySerializer(serializers.ModelSerializer):
    posts_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description", "posts_count")
        read_only_fields = ("slug",)

    def get_posts_count(self, obj):
        if hasattr(obj, "published_posts_count"):
            return obj.published_posts_count
        return obj.posts.filter(status=Post.Status.PUBLISHED).count()


class TagSerializer(serializers.ModelSerializer):
    posts_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ("id", "name", "slug", "posts_count")
        read_only_fields = ("slug",)

    def get_posts_count(self, obj):
        if hasattr(obj, "published_posts_count"):
            return obj.published_posts_count
        return obj.posts.filter(status=Post.Status.PUBLISHED).count()


# ---------------------------------------------------------------------------
# Blog: Post
# ---------------------------------------------------------------------------
class CategoryMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class PostListSerializer(serializers.ModelSerializer):
    category = CategoryMiniSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Post
        fields = (
            "id", "title", "slug", "excerpt", "cover_image", "category",
            "tags", "status", "published_at", "views_count", "reading_time",
            "is_featured", "likes_count", "comments_count", "created_at",
        )


class PostDetailSerializer(serializers.ModelSerializer):
    category = CategoryMiniSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    author = serializers.CharField(source="author.username", read_only=True)
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    related_posts = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id", "title", "slug", "excerpt", "content", "cover_image",
            "category", "tags", "author", "status", "published_at",
            "views_count", "reading_time", "is_featured", "likes_count",
            "comments_count", "is_liked", "related_posts",
            "created_at", "updated_at",
        )

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_comments_count(self, obj):
        return obj.comments.filter(is_approved=True).count()

    def get_is_liked(self, obj):
        visitor_id = self.context.get("visitor_id")
        if not visitor_id:
            return False
        return obj.likes.filter(visitor_id=visitor_id).exists()

    def get_related_posts(self, obj):
        qs = (
            Post.objects.filter(
                category=obj.category, status=Post.Status.PUBLISHED
            )
            .exclude(pk=obj.pk)
            .order_by("-published_at")[:3]
        )
        return PostRelatedSerializer(qs, many=True, context=self.context).data


class PostRelatedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ("id", "title", "slug", "excerpt", "cover_image", "reading_time")


class PostWriteSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source="category"
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all(), source="tags", required=False
    )

    class Meta:
        model = Post
        fields = (
            "id", "title", "slug", "excerpt", "content", "cover_image",
            "category_id", "tag_ids", "status", "published_at", "views_count",
            "reading_time", "is_featured",
        )
        read_only_fields = ("slug", "published_at", "views_count", "reading_time")

    def validate_title(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Title must be at least 5 characters.")
        return value

    def validate(self, attrs):
        status = attrs.get("status", getattr(self.instance, "status", Post.Status.DRAFT))
        content = attrs.get("content", getattr(self.instance, "content", ""))
        category = attrs.get("category", getattr(self.instance, "category", None))
        if status == Post.Status.PUBLISHED:
            if not category:
                raise serializers.ValidationError(
                    {"category_id": "A published post must have a category."}
                )
            if len(content.strip()) < 100:
                raise serializers.ValidationError(
                    {"content": "A published post needs at least 100 characters of content."}
                )
        return attrs


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------
class CommentPublicSerializer(serializers.ModelSerializer):
    """Public view of a comment — email is never exposed (S-8)."""

    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ("id", "name", "website", "content", "parent", "replies", "created_at")

    def get_replies(self, obj):
        replies = obj.replies.filter(is_approved=True).order_by("created_at")
        return CommentReplySerializer(replies, many=True, context=self.context).data


class CommentReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ("id", "name", "website", "content", "parent", "created_at")


class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ("id", "name", "email", "website", "content", "parent")

    def validate_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters.")
        return value

    def validate_content(self, value):
        length = len(value.strip())
        if length < 5 or length > 1000:
            raise serializers.ValidationError(
                "Comment must be between 5 and 1000 characters."
            )
        return value

    def validate_parent(self, value):
        if value and value.parent_id:
            raise serializers.ValidationError("Replies can only be one level deep.")
        return value


class CommentModerationSerializer(serializers.ModelSerializer):
    """Owner-only moderation view — includes email and approval flag."""

    post_title = serializers.CharField(source="post.title", read_only=True)
    post_slug = serializers.CharField(source="post.slug", read_only=True)

    class Meta:
        model = Comment
        fields = (
            "id", "post", "post_title", "post_slug", "name", "email",
            "website", "content", "parent", "is_approved", "created_at",
        )
        read_only_fields = ("post", "name", "email", "website", "content", "parent")


# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------
class ContactMessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ("id", "name", "email", "subject", "message")

    def validate_message(self, value):
        length = len(value.strip())
        if length < 10 or length > 2000:
            raise serializers.ValidationError(
                "Message must be between 10 and 2000 characters."
            )
        return value


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = (
            "id", "name", "email", "subject", "message", "is_read", "created_at",
        )
