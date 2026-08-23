"""
B-20. Signals.

- post_save on Comment: when a new, unapproved comment is created, send the
  owner a "New comment awaiting approval" email via the console backend.
- post_delete on Post: remove the cover image file from disk.
"""
from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Comment, Post


@receiver(post_save, sender=Comment)
def notify_owner_of_new_comment(sender, instance, created, **kwargs):
    if created and not instance.is_approved:
        send_mail(
            subject="New comment awaiting approval",
            message=(
                f'{instance.name} commented on post #{instance.post_id}:\n\n'
                f'"{instance.content[:200]}"\n\n'
                f"Approve it in the dashboard moderation queue."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.OWNER_NOTIFY_EMAIL],
            fail_silently=True,
        )


@receiver(post_delete, sender=Post)
def delete_post_cover_image(sender, instance, **kwargs):
    if instance.cover_image:
        instance.cover_image.delete(save=False)
