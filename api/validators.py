"""File/image validators used by both models and serializers (B-21)."""
import os

from django.core.exceptions import ValidationError

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
MAX_IMAGE_BYTES = 2 * 1024 * 1024   # 2 MB
MAX_RESUME_BYTES = 5 * 1024 * 1024  # 5 MB


def validate_image_file(file):
    """Images: max 2 MB, only .jpg/.jpeg/.png/.webp."""
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in IMAGE_EXTENSIONS:
        raise ValidationError(
            f"Unsupported image type '{ext}'. Allowed: JPG, JPEG, PNG, WEBP."
        )
    if file.size and file.size > MAX_IMAGE_BYTES:
        raise ValidationError("Image too large. Maximum size is 2 MB.")


def validate_resume_file(file):
    """Resume: PDF only, max 5 MB."""
    ext = os.path.splitext(file.name)[1].lower()
    if ext != ".pdf":
        raise ValidationError("Resume must be a PDF file.")
    if file.size and file.size > MAX_RESUME_BYTES:
        raise ValidationError("Resume too large. Maximum size is 5 MB.")
