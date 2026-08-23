"""
DRF views for DevFolio.

Public reads, owner-only writes. Draft posts and unapproved comments are
filtered out of every public response at the queryset level (S-3).
"""
import datetime

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Count, F, Q, Sum
from django.db.models.deletion import ProtectedError
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .filters import PostFilter, ProjectFilter, SkillFilter
from .models import (
    Category,
    Comment,
    ContactMessage,
    Education,
    Experience,
    PostLike,
    Post,
    Profile,
    Project,
    Skill,
    Tag,
)
from .pagination import (
    CommentPagination,
    DefaultPagination,
    MessagePagination,
    PostPagination,
    ProjectPagination,
)
from .permissions import IsOwner, IsOwnerOrReadOnly, is_owner
from .serializers import (
    CategorySerializer,
    ChangePasswordSerializer,
    CommentCreateSerializer,
    CommentModerationSerializer,
    CommentPublicSerializer,
    ContactMessageCreateSerializer,
    ContactMessageSerializer,
    EducationSerializer,
    ExperienceSerializer,
    LoginSerializer,
    PostDetailSerializer,
    PostListSerializer,
    PostWriteSerializer,
    ProfileSerializer,
    ProjectSerializer,
    SkillSerializer,
    TagSerializer,
    UserSerializer,
)
from .throttles import CommentThrottle, ContactThrottle, LikeThrottle

VIEW_COOLDOWN_SECONDS = 60 * 60 * 6  # 6h — a refresh won't re-count (B-16)


def get_visitor_id(request):
    return request.headers.get("X-Visitor-Id") or ""


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class LogoutView(APIView):
    permission_classes = [IsOwner]

    def post(self, request):
        try:
            RefreshToken(request.data.get("refresh")).blacklist()
        except (TokenError, AttributeError):
            return Response(
                {"detail": "Invalid or missing refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(APIView):
    permission_classes = [IsOwner]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(GenericAPIView):
    permission_classes = [IsOwner]
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response({"detail": "Password updated successfully."})


# ---------------------------------------------------------------------------
# Profile (singleton)
# ---------------------------------------------------------------------------
class ProfileView(APIView):
    permission_classes = [IsOwnerOrReadOnly]

    def get(self, request):
        profile = Profile.get_solo()
        if profile is None:
            return Response(
                {"detail": "Profile has not been set up yet."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ProfileSerializer(profile, context={"request": request}).data)

    def patch(self, request):
        profile = Profile.get_solo()
        if profile is None:
            profile = Profile()
        serializer = ProfileSerializer(
            profile, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Skills / Experience / Education
# ---------------------------------------------------------------------------
class SkillViewSet(viewsets.ModelViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = SkillFilter
    search_fields = ["name"]
    ordering_fields = ["display_order", "proficiency", "name"]
    ordering = ["display_order", "-proficiency"]


class ExperienceViewSet(viewsets.ModelViewSet):
    queryset = Experience.objects.all()
    serializer_class = ExperienceSerializer
    permission_classes = [IsOwnerOrReadOnly]
    ordering = ["-start_date"]


class EducationViewSet(viewsets.ModelViewSet):
    queryset = Education.objects.all()
    serializer_class = EducationSerializer
    permission_classes = [IsOwnerOrReadOnly]


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.prefetch_related("tech_stack").all()
    serializer_class = ProjectSerializer
    permission_classes = [IsOwnerOrReadOnly]
    lookup_field = "slug"
    pagination_class = ProjectPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProjectFilter
    search_fields = ["title", "summary", "description"]
    ordering_fields = ["completed_date", "display_order", "created_at", "title"]
    ordering = ["display_order", "-completed_date"]


# ---------------------------------------------------------------------------
# Blog: Category / Tag
# ---------------------------------------------------------------------------
class _PublishedCountMixin:
    """Annotate published-posts count so the serializer avoids N+1 queries."""

    def get_queryset(self):
        return super().get_queryset().annotate(
            published_posts_count=Count(
                "posts", filter=Q(posts__status=Post.Status.PUBLISHED), distinct=True
            )
        )

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                "This category is used by one or more posts and cannot be deleted."
            )


class CategoryViewSet(_PublishedCountMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsOwnerOrReadOnly]
    lookup_field = "slug"
    pagination_class = None


class TagViewSet(_PublishedCountMixin, viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsOwnerOrReadOnly]
    lookup_field = "slug"
    pagination_class = None


# ---------------------------------------------------------------------------
# Blog: Posts
# ---------------------------------------------------------------------------
class PostViewSet(viewsets.ModelViewSet):
    permission_classes = [IsOwnerOrReadOnly]
    lookup_field = "slug"
    pagination_class = PostPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = PostFilter
    search_fields = ["title", "excerpt", "content"]
    ordering_fields = ["published_at", "views_count", "likes_count", "title", "created_at"]
    ordering = ["-published_at"]

    def get_queryset(self):
        qs = (
            Post.objects.select_related("category", "author")
            .prefetch_related("tags")
            .annotate(
                likes_count=Count("likes", distinct=True),
                comments_count=Count(
                    "comments", filter=Q(comments__is_approved=True), distinct=True
                ),
            )
        )
        # Owner may request drafts explicitly; visitors only ever see PUBLISHED.
        if is_owner(self.request.user):
            status_param = self.request.query_params.get("status")
            if status_param == "all":
                return qs
            if status_param in (Post.Status.DRAFT, Post.Status.PUBLISHED):
                return qs.filter(status=status_param)
            return qs  # owner default: everything
        return qs.filter(status=Post.Status.PUBLISHED)

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return PostWriteSerializer
        if self.action == "retrieve":
            return PostDetailSerializer
        return PostListSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["visitor_id"] = get_visitor_id(self.request)
        return ctx

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        post = self.get_object()
        self._count_view(request, post)
        serializer = self.get_serializer(post)
        return Response(serializer.data)

    def _count_view(self, request, post):
        # B-16: guard against double counting (refresh / React StrictMode).
        if is_owner(request.user):
            return
        visitor_key = get_visitor_id(request) or request.META.get("REMOTE_ADDR", "anon")
        cache_key = f"viewed:{post.slug}:{visitor_key}"
        if cache.add(cache_key, 1, timeout=VIEW_COOLDOWN_SECONDS):
            Post.objects.filter(pk=post.pk).update(views_count=F("views_count") + 1)
            post.views_count += 1

    # ---- like toggle (public) ------------------------------------------
    @action(detail=True, methods=["post"], permission_classes=[AllowAny],
            throttle_classes=[LikeThrottle])
    def like(self, request, slug=None):
        post = self.get_object()
        visitor_id = get_visitor_id(request)
        if not visitor_id:
            return Response(
                {"detail": "X-Visitor-Id header is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        like = PostLike.objects.filter(post=post, visitor_id=visitor_id).first()
        if like:
            like.delete()
            liked = False
        else:
            PostLike.objects.create(
                post=post,
                visitor_id=visitor_id,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            liked = True
        return Response({"liked": liked, "likes_count": post.likes.count()})

    # ---- comments (public list + create) -------------------------------
    @action(detail=True, methods=["get", "post"], permission_classes=[AllowAny])
    def comments(self, request, slug=None):
        post = self.get_object()
        if request.method == "POST":
            serializer = CommentCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(post=post, is_approved=False)
            return Response(
                {
                    "detail": "Your comment is awaiting approval.",
                    "comment": {"id": serializer.instance.id},
                },
                status=status.HTTP_201_CREATED,
            )
        # GET: approved, top-level comments newest first (replies nested).
        top_level = (
            post.comments.filter(is_approved=True, parent__isnull=True)
            .order_by("-created_at")
        )
        data = CommentPublicSerializer(
            top_level, many=True, context=self.get_serializer_context()
        ).data
        return Response(data)

    def get_throttles(self):
        if self.action == "comments" and self.request.method == "POST":
            return [CommentThrottle()]
        return super().get_throttles()


# ---------------------------------------------------------------------------
# Comment moderation (owner only)
# ---------------------------------------------------------------------------
class CommentModerationViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.select_related("post").all()
    serializer_class = CommentModerationSerializer
    permission_classes = [IsOwner]
    pagination_class = CommentPagination
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        is_approved = self.request.query_params.get("is_approved")
        if is_approved is not None:
            qs = qs.filter(is_approved=is_approved.lower() == "true")
        post_slug = self.request.query_params.get("post")
        if post_slug:
            qs = qs.filter(post__slug=post_slug)
        # Pending first, then newest.
        return qs.order_by("is_approved", "-created_at")


# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------
class ContactMessageViewSet(viewsets.ModelViewSet):
    queryset = ContactMessage.objects.all()
    pagination_class = MessagePagination
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return ContactMessageCreateSerializer
        return ContactMessageSerializer

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        return [IsOwner()]

    def get_throttles(self):
        if self.action == "create":
            return [ContactThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        qs = super().get_queryset()
        is_read = self.request.query_params.get("is_read")
        if is_read is not None:
            qs = qs.filter(is_read=is_read.lower() == "true")
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Thanks for reaching out — I'll get back to you soon."},
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Dashboard stats (owner only) — ORM aggregation, no Python loops over rows
# ---------------------------------------------------------------------------
class DashboardStatsView(APIView):
    permission_classes = [IsOwner]

    def get(self, request):
        posts = Post.objects.all()
        comments = Comment.objects.all()

        top_posts = list(
            posts.annotate(likes_count=Count("likes", distinct=True))
            .order_by("-views_count")[:5]
            .values("title", "slug", "views_count", "likes_count")
        )
        recent_comments = list(
            comments.select_related("post")
            .order_by("-created_at")[:5]
            .values("id", "name", "content", "is_approved", "post__title", "created_at")
        )

        # posts_per_month for the last 6 months (aggregated, zero-filled skeleton).
        today = timezone.now().date().replace(day=1)
        months = []
        cursor = today
        for _ in range(6):
            months.append(cursor)
            year = cursor.year - 1 if cursor.month == 1 else cursor.year
            month = 12 if cursor.month == 1 else cursor.month - 1
            cursor = datetime.date(year, month, 1)
        months.reverse()
        raw = (
            posts.filter(
                status=Post.Status.PUBLISHED, published_at__date__gte=months[0]
            )
            .annotate(m=TruncMonth("published_at"))
            .values("m")
            .annotate(c=Count("id"))
        )
        counts = {row["m"].date().replace(day=1): row["c"] for row in raw if row["m"]}
        posts_per_month = [
            {"month": m.strftime("%Y-%m"), "count": counts.get(m, 0)} for m in months
        ]

        data = {
            "total_posts": posts.count(),
            "published_posts": posts.filter(status=Post.Status.PUBLISHED).count(),
            "draft_posts": posts.filter(status=Post.Status.DRAFT).count(),
            "total_projects": Project.objects.count(),
            "total_skills": Skill.objects.count(),
            "total_comments": comments.count(),
            "pending_comments": comments.filter(is_approved=False).count(),
            "total_likes": PostLike.objects.count(),
            "total_views": posts.aggregate(v=Sum("views_count"))["v"] or 0,
            "unread_messages": ContactMessage.objects.filter(is_read=False).count(),
            "top_posts": top_posts,
            "recent_comments": recent_comments,
            "posts_per_month": posts_per_month,
        }
        return Response(data)
