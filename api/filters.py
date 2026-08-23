"""B-15. django-filter FilterSets for skills, projects and posts."""
import django_filters as filters

from .models import Post, Project, Skill


class SkillFilter(filters.FilterSet):
    category = filters.CharFilter(field_name="category", lookup_expr="iexact")
    is_featured = filters.BooleanFilter(field_name="is_featured")

    class Meta:
        model = Skill
        fields = ("category", "is_featured")


class ProjectFilter(filters.FilterSet):
    category = filters.CharFilter(field_name="category", lookup_expr="iexact")
    is_featured = filters.BooleanFilter(field_name="is_featured")
    # ?tech=<skill id> or ?tech=<skill name>
    tech = filters.CharFilter(method="filter_tech")

    class Meta:
        model = Project
        fields = ("category", "is_featured", "tech")

    def filter_tech(self, queryset, name, value):
        if value.isdigit():
            return queryset.filter(tech_stack__id=int(value)).distinct()
        return queryset.filter(tech_stack__name__iexact=value).distinct()


class PostFilter(filters.FilterSet):
    category = filters.CharFilter(field_name="category__slug", lookup_expr="iexact")
    tag = filters.CharFilter(field_name="tags__slug", lookup_expr="iexact")
    is_featured = filters.BooleanFilter(field_name="is_featured")

    class Meta:
        model = Post
        fields = ("category", "tag", "is_featured")
