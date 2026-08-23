"""B-18. Pagination classes with count / next / previous / results."""
from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class PostPagination(DefaultPagination):
    page_size = 6  # blog posts: 6 per page


class ProjectPagination(DefaultPagination):
    page_size = 9  # projects: 9 per page


class CommentPagination(DefaultPagination):
    page_size = 10  # moderation list: 10 per page


class MessagePagination(DefaultPagination):
    page_size = 10  # contact inbox: 10 per page
