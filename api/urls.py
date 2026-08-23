"""API URL routing. Base path is /api/ (mounted in config/urls.py)."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CategoryViewSet,
    ChangePasswordView,
    CommentModerationViewSet,
    ContactMessageViewSet,
    DashboardStatsView,
    EducationViewSet,
    ExperienceViewSet,
    LoginView,
    LogoutView,
    MeView,
    PostViewSet,
    ProfileView,
    ProjectViewSet,
    SkillViewSet,
    TagViewSet,
)

router = DefaultRouter()
router.register("skills", SkillViewSet, basename="skill")
router.register("experiences", ExperienceViewSet, basename="experience")
router.register("education", EducationViewSet, basename="education")
router.register("projects", ProjectViewSet, basename="project")
router.register("categories", CategoryViewSet, basename="category")
router.register("tags", TagViewSet, basename="tag")
router.register("posts", PostViewSet, basename="post")
router.register("comments", CommentModerationViewSet, basename="comment")
router.register("contact", ContactMessageViewSet, basename="contact")

urlpatterns = [
    # Auth (NOTE: no register endpoint anywhere — B-14 / S-2)
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="change_password"),
    # Profile (singleton — not a router/list)
    path("profile/", ProfileView.as_view(), name="profile"),
    # Dashboard
    path("dashboard/stats/", DashboardStatsView.as_view(), name="dashboard_stats"),
    # Everything else
    path("", include(router.urls)),
]
