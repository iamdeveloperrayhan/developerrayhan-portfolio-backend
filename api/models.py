"""
DevFolio data models.

Every model carries created_at (auto_now_add) and updated_at (auto_now)
unless the spec states otherwise. PostLike keeps only created_at.
"""
import math

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from .validators import validate_image_file, validate_resume_file


def unique_slugify(instance, value, slug_field_name="slug"):
    """Return a unique slug for ``instance`` derived from ``value``."""
    base = slugify(value)[:250] or "item"
    ModelClass = instance.__class__
    slug = base
    counter = 2
    qs = ModelClass.objects.all()
    if instance.pk:
        qs = qs.exclude(pk=instance.pk)
    while qs.filter(**{slug_field_name: slug}).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# B-2. Profile — singleton
# ---------------------------------------------------------------------------
class Profile(TimeStampedModel):
    full_name = models.CharField(max_length=120)
    headline = models.CharField(max_length=160, help_text='e.g. "Full-Stack Developer"')
    bio = models.TextField()
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    location = models.CharField(max_length=120, blank=True)
    avatar = models.ImageField(
        upload_to="avatars/", blank=True, null=True, validators=[validate_image_file]
    )
    resume = models.FileField(
        upload_to="resumes/", blank=True, null=True, validators=[validate_resume_file]
    )
    github_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    x_url = models.URLField(blank=True)
    website_url = models.URLField(blank=True)
    years_of_experience = models.PositiveIntegerField(default=0)
    is_available_for_hire = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profile"

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        # Enforce singleton: only one Profile row may ever exist.
        if not self.pk and Profile.objects.exists():
            raise ValidationError("Only one Profile instance is allowed.")
        return super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        return cls.objects.first()


# ---------------------------------------------------------------------------
# B-3. Skill
# ---------------------------------------------------------------------------
class Skill(TimeStampedModel):
    class Category(models.TextChoices):
        FRONTEND = "FRONTEND", "Frontend"
        BACKEND = "BACKEND", "Backend"
        DATABASE = "DATABASE", "Database"
        DEVOPS = "DEVOPS", "DevOps"
        TOOLS = "TOOLS", "Tools"
        SOFT_SKILL = "SOFT_SKILL", "Soft Skill"

    name = models.CharField(max_length=80, unique=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    proficiency = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    icon = models.CharField(
        max_length=80, blank=True, help_text="Icon name (e.g. 'react') or leave blank"
    )
    icon_image = models.ImageField(
        upload_to="skills/", blank=True, null=True, validators=[validate_image_file]
    )
    display_order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["display_order", "-proficiency", "name"]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# B-4. Experience
# ---------------------------------------------------------------------------
class Experience(TimeStampedModel):
    class EmploymentType(models.TextChoices):
        FULL_TIME = "FULL_TIME", "Full-time"
        PART_TIME = "PART_TIME", "Part-time"
        INTERNSHIP = "INTERNSHIP", "Internship"
        FREELANCE = "FREELANCE", "Freelance"
        CONTRACT = "CONTRACT", "Contract"

    company = models.CharField(max_length=120)
    role = models.CharField(max_length=120)
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME
    )
    location = models.CharField(max_length=120, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    company_url = models.URLField(blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-start_date", "display_order"]

    def __str__(self):
        return f"{self.role} @ {self.company}"


# ---------------------------------------------------------------------------
# B-5. Education
# ---------------------------------------------------------------------------
class Education(TimeStampedModel):
    institution = models.CharField(max_length=160)
    degree = models.CharField(max_length=160)
    field_of_study = models.CharField(max_length=160)
    start_year = models.PositiveIntegerField()
    end_year = models.PositiveIntegerField(null=True, blank=True)
    grade = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-start_year", "display_order"]
        verbose_name_plural = "Education"

    def __str__(self):
        return f"{self.degree} — {self.institution}"


# ---------------------------------------------------------------------------
# B-6. Project
# ---------------------------------------------------------------------------
class Project(TimeStampedModel):
    class Category(models.TextChoices):
        WEB = "WEB", "Web"
        MOBILE = "MOBILE", "Mobile"
        API = "API", "API"
        ML = "ML", "Machine Learning"
        OTHER = "OTHER", "Other"

    title = models.CharField(max_length=160, unique=True)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    summary = models.CharField(max_length=200)
    description = models.TextField()
    cover_image = models.ImageField(
        upload_to="projects/", blank=True, null=True, validators=[validate_image_file]
    )
    tech_stack = models.ManyToManyField(Skill, related_name="projects", blank=True)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.WEB
    )
    live_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    is_featured = models.BooleanField(default=False)
    completed_date = models.DateField(null=True, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "-completed_date", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.title)
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# B-7. Category (blog)
# ---------------------------------------------------------------------------
class Category(TimeStampedModel):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# B-8. Tag
# ---------------------------------------------------------------------------
class Tag(TimeStampedModel):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=80, unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# B-9. Post (blog)
# ---------------------------------------------------------------------------
class Post(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    excerpt = models.CharField(max_length=300)
    content = models.TextField(help_text="Markdown — see README")
    cover_image = models.ImageField(
        upload_to="posts/", blank=True, null=True, validators=[validate_image_file]
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="posts"
    )
    tags = models.ManyToManyField(Tag, related_name="posts", blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.DRAFT
    )
    published_at = models.DateTimeField(null=True, blank=True)
    views_count = models.PositiveIntegerField(default=0)
    reading_time = models.PositiveIntegerField(default=1, help_text="minutes")
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.title)
        # reading_time computed from word count (~200 wpm), never hand-entered.
        words = len(self.content.split()) if self.content else 0
        self.reading_time = max(1, math.ceil(words / 200))
        # published_at set once, on the first DRAFT -> PUBLISHED transition.
        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# B-10. PostLike  (created_at only)
# ---------------------------------------------------------------------------
class PostLike(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    visitor_id = models.CharField(max_length=64)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "visitor_id")

    def __str__(self):
        return f"like:{self.post_id}:{self.visitor_id}"


# ---------------------------------------------------------------------------
# B-11. Comment
# ---------------------------------------------------------------------------
class Comment(TimeStampedModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    name = models.CharField(max_length=80)
    email = models.EmailField()  # never returned by the public API (S-8)
    website = models.URLField(blank=True)
    content = models.TextField()
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
    )
    is_approved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} on {self.post_id}"

    def save(self, *args, **kwargs):
        # One level of replies only: a reply's parent must be a top-level comment.
        if self.parent and self.parent.parent_id:
            raise ValidationError("Only one level of replies is allowed.")
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# B-12. ContactMessage
# ---------------------------------------------------------------------------
class ContactMessage(TimeStampedModel):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} — {self.name}"
